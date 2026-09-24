"""
Idempotent webhook handler template
------------------------------------
Most systems only guarantee "at-least-once" delivery for webhooks, not
"exactly-once". If a response times out, gets dropped, or the network
hiccups, the sender retries. Your endpoint then sees the same event twice.

This template stops duplicate processing using an idempotency key: a value
that uniquely identifies one specific event (not the record it affects).
Before acting on an event, check whether that key has already been
processed. If it has, acknowledge and skip. If not, process it and store
the key atomically so a second, near-simultaneous duplicate can't slip
through the same check.

Swap the storage backend (this uses SQLite for a drop-in, zero-setup
example) for Redis or your own database in production. The pattern stays
identical.
"""

import sqlite3
import time
from contextlib import contextmanager

from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

DB_PATH = "webhook_events.db"
RETENTION_HOURS = 72  # most providers stop retrying well before this


def init_db():
    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_events (
                event_id TEXT PRIMARY KEY,
                processed_at REAL NOT NULL
            )
            """
        )


@contextmanager
def get_db():
    db = sqlite3.connect(DB_PATH, isolation_level=None)  # autocommit off
    try:
        yield db
    finally:
        db.close()


def already_processed(db: sqlite3.Connection, event_id: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM processed_events WHERE event_id = ?", (event_id,)
    ).fetchone()
    return row is not None


def mark_processed(db: sqlite3.Connection, event_id: str) -> bool:
    """
    Returns True if this call actually inserted the key (first time seen).
    Returns False if another request already inserted it first, this is
    the atomic check that closes the race condition between two
    near-simultaneous duplicates.
    """
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            "INSERT INTO processed_events (event_id, processed_at) VALUES (?, ?)",
            (event_id, time.time()),
        )
        db.execute("COMMIT")
        return True
    except sqlite3.IntegrityError:
        db.execute("ROLLBACK")
        return False


def cleanup_old_events(db: sqlite3.Connection):
    cutoff = time.time() - (RETENTION_HOURS * 3600)
    db.execute("DELETE FROM processed_events WHERE processed_at < ?", (cutoff,))


def process_event(payload: dict):
    """
    Your actual business logic goes here. This is the part that should
    only ever run once per real event, everything above this function
    exists to guarantee that.
    """
    print(f"Processing event: {payload}")
    # e.g. charge a customer, create a CRM record, send a notification, etc.


@app.post("/webhook")
async def handle_webhook(request: Request):
    payload = await request.json()

    # Adjust this to match your provider's actual event ID field.
    # Stripe uses payload["id"], GitHub uses request.headers["X-GitHub-Delivery"],
    # Shopify uses request.headers["X-Shopify-Webhook-Id"], etc.
    event_id = payload.get("id")
    if not event_id:
        raise HTTPException(status_code=400, detail="Missing event id")

    with get_db() as db:
        if already_processed(db, event_id):
            # Acknowledge with 200 so the sender doesn't retry again.
            # Do NOT reprocess.
            return {"status": "already processed"}

        if not mark_processed(db, event_id):
            # Lost the race to another concurrent request handling the
            # same event, that request is processing it, we don't.
            return {"status": "already processed"}

        cleanup_old_events(db)
        process_event(payload)

    return {"status": "processed"}


@app.on_event("startup")
def startup():
    init_db()
