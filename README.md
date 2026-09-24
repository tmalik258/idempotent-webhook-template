# Idempotent Webhook Handler Template

Free template. Two versions, same pattern: a Python/FastAPI implementation and an n8n workflow you can import directly.

## The problem this solves

Most systems only guarantee "at-least-once" webhook delivery, not "exactly-once". If your endpoint times out, drops a response, or the network hiccups, the sender retries. Without protection, you process the same event twice, a customer gets charged twice, two calendar bookings land on the same slot, two identical support tickets get created.

## The fix

Every incoming event gets an idempotency key, something that uniquely identifies that specific event, not the record it affects (a Stripe event ID, a GitHub delivery ID, a Shopify webhook ID). Before acting on an event, check whether you've already processed that key. If you have, acknowledge and skip. If you haven't, process it and store the key, atomically, so two near-simultaneous duplicates can't both slip through the check.

## What's in this template

- `webhook_handler.py` — a complete, runnable FastAPI endpoint using SQLite for zero-setup local testing. Swap SQLite for Redis or your production database, the pattern stays the same.
- `n8n-idempotent-webhook.json` — the same pattern as an importable n8n workflow. Import it directly into your n8n instance (Workflows → Import from File), swap the Postgres nodes for whatever database you're using, and drop your own logic into the "Process Event" node.

## Using this

1. Pick the version that matches your stack.
2. Swap the event ID extraction to match your actual webhook provider's payload shape (comments in both files show where).
3. Swap the storage layer for your production database if you're not already using Postgres/SQLite.
4. Drop your real business logic into the marked section.
5. Set a retention window for stored event IDs, most providers stop retrying within 24-72 hours, so you don't need to store every ID forever.

## If this doesn't fully solve your case

This template handles the duplicate-event problem specifically. If you're also seeing CRM drift, agents that don't know when to stop and ask a human, or pipelines that die halfway through and leave records in a broken state, those are different (related) problems with different fixes. Happy to take a free look at your specific setup, message me and describe what's breaking.

Talha Malik
AI Automation & Full-Stack Developer, Top Rated on Upwork
linkedin.com/in/tmalikk
