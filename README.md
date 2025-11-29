# SHPPD Zara Stock Tracker

This repository contains a two-service system that lets Telegram users follow Zara product URLs and receive alerts when any size returns to stock. A Python Flask API talks to Zara's public website, parses product information, polls availability, and notifies a Node.js Telegram bot over HTTP. A Docker Compose file ties the services together (plus a placeholder Postgres instance for future persistence work).

## Repository Layout

- `api-connect/` – Flask API, Zara scraping utilities, APScheduler-based tracker, and unit tests.
- `telegram-bot/` – Node/TypeScript Telegram bot that exposes `/add`, `/list`, and `/event` endpoints.
- `docker-compose.yml` – Describes the `api`, `bot`, and `db` services plus shared network/volume.
- `rebuild.sh` – Convenience script to rebuild local Docker images for the API and bot services.
- `test.http` – REST Client snippets for manual API exploration from an editor.

## Architecture Overview

1. **Telegram Channel** – Users interact with the bot via `/add <url>` to follow a Zara product or `/list` to view tracked items. The bot sends HTTP requests to the API for these actions.
2. **API Connector (Flask)** – Exposes:
   - `GET /zara/item?url=...`: returns normalized product metadata and current size availability.
   - `GET /follow/<chat_id>`: lists URLs tracked for a chat.
   - `POST /follow/<chat_id>`: validates a product URL, stores it, and schedules stock polling.
3. **Zara Scraper Layer** – `zara/api.py` fetches the Zara product page, extracts JSON payloads via BeautifulSoup, and calls the stock availability endpoint. `zara/util.py` parses share links and maps stock tuples to friendly size labels.
4. **Tracker & Notifications** – `tracker.py` schedules APScheduler jobs (default 5-second interval) to call Zara APIs. When any size is back in stock, it formats a message and POSTs to the bot's `POST /event` endpoint (`http://telegram-bot:3000/event`), which relays the alert to the requesting user.
5. **Persistence** – A Postgres-backed `Persist` stores users, products, and subscriptions (many-to-many). Products are keyed by `(productId, name, v1)` and reused across subscribers. Subscriptions can record selected sizes so the bot can prompt users with a keyboard when multiple sizes exist.

## Environment Variables

- `TELEGRAM_TOKEN` (required by `telegram-bot`): Telegram Bot API token.
- `DATABASE_URL` (declared for the API container): points to Postgres; unused today but reserved for later.

## Local Development

### Prerequisites

- Docker + Docker Compose (recommended path).
- Alternatively: Python 3.12, Node.js 16+, and `pip`/`npm`.

### Via Docker Compose

```bash
./rebuild.sh               # optional: rebuild images after code changes
docker compose up --build  # from repo root
```

Services:

- API reachable at `http://localhost:5508`.
- Telegram bot listens on `http://localhost:3000` for webhook-style event posts but connects to Telegram over polling. Provide `TELEGRAM_TOKEN` via environment or `.env` (Compose uses container env vars).

### Running Bare-Metal

```bash
# API
cd api-connect
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python server.py

# Telegram bot
cd telegram-bot
npm install
TELEGRAM_TOKEN=... npm start
```

Unit tests (API only):

```bash
cd api-connect
pytest
```

## Key API & Bot Interfaces

| Interface | Description |
| --- | --- |
| `GET /zara/item?url=<zara-url>` | Parses Zara share/product URLs and returns `{name, productId, url, sizes, v1}` with `sizes` mapped to `true/false`. |
| `POST /follow/<chat_id>` (JSON `{ "url": "<zara-url>" }`) | Validates the URL, stores it, and starts a polling job. |
| `GET /follow/<chat_id>` | Lists tracked URLs for the chat. |
| Telegram `/add <url>` | Calls the API `POST /follow` endpoint. |
| Telegram `/list` | Calls the API `GET /follow` endpoint. |
| `POST /event` (bot) | Internal endpoint for the API to send `{userId, message}` alerts; bot forwards the message. |

## Product Requirements Document (PRD)

### Problem Statement

Fashion drops sell out quickly on Zara. Users want a simple way to monitor specific items and receive instant notifications when any size comes back in stock without constantly refreshing product pages.

### Goals

1. Enable Telegram users to subscribe to Zara product URLs and receive availability alerts in near real time.
2. Provide a self-hostable stack that scrapes only publicly available Zara endpoints.
3. Keep operational complexity low: a single API service plus a Telegram bot, orchestrated via Docker.

### Non-Goals

- Managing inventory for stores other than Zara.
- Supporting checkout or purchase flows.
- Providing a production-grade persistence layer (yet).

### Target Users & User Stories

- **Sneaker/fashion enthusiasts**: "As a Telegram user, I want to subscribe to a Zara product so that I know when it’s back in stock."
- **Casual shoppers**: "As a user, I want to list products I am tracking to see what is still pending."
- **Operators**: "As a self-hosting maintainer, I want clear deployment steps so I can run the services on my own server."

### Functional Requirements

1. Parse any Zara share or locale-specific product URL to extract `product` slug and `v1` identifier.
2. Normalize product metadata (name, URL, SKU-to-size mapping) for downstream use.
3. Poll Zara’s availability endpoint on an interval per subscribed URL; interval must be configurable in code.
4. Notify the requester via Telegram when any tracked size is `in_stock`.
5. Allow users to request the list of URLs they currently track.
6. Provide health/trace logging for scraping and notification flows.

### Non-Functional Requirements

- **Latency**: Average end-to-end notification delay <= polling interval (currently 5 seconds).
- **Reliability**: Scheduler must survive transient Zara failures by keeping jobs active.
- **Security**: Telegram token must not be logged; restrict API endpoints to bot interactions in production.
- **Maintainability**: Tests cover URL parsing and size mapping logic; code structured per component.

### Success Metrics

- Time-to-notification after Zara reports `in_stock`.
- Number of successful subscription flows vs. failures.
- Bot uptime and number of processed `/add` commands.

### Dependencies & Risks

- Dependent on Zara website structure; DOM/layout changes may break scraping.
- In-memory persistence means restarts drop subscriptions (introduce Postgres usage to fix).
- Telegram Bot API limits could throttle frequent messaging if many users subscribe simultaneously.

### Future Enhancements

1. Replace `Persist` with the provided Postgres instance for durable tracking and multi-instance scaling.
2. Add `/remove <url>` and `/stop` commands.
3. Allow users to set size filters or store preferences.
4. Add authentication/authorization for API endpoints.
5. Surface status dashboards or metrics endpoints for observability.

---

With this README + PRD you can understand the system’s purpose, extend requirements, and deploy the service quickly. Open issues or architecture ideas can now be tracked against the PRD sections above.
