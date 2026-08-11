# URL Shortener + Caching Service

A URL shortening service built with production-grade reliability patterns — Redis
cache-aside caching, token-bucket rate limiting, and client-supplied idempotency
keys to prevent duplicate writes under retry conditions.

## Why this project

Most URL shortener tutorials stop at "generate a random string and save it to a
database." This one doesn't.

URL shorteners are read-heavy — there are far more redirects than link creations —
so the architecture here is built around making that read path fast and resilient.
The write path handles the real edge cases too: collisions, abuse, and retries.

---

## Tech stack

| Layer | Tool |
|-------|------|
| API framework | FastAPI |
| Primary storage | PostgreSQL |
| Cache + rate limiting | Redis |
| ORM | SQLAlchemy |
| Local infra | Docker Compose |

---

## Getting started

### 1. Start Postgres and Redis

```bash
docker compose up -d
```

This brings up PostgreSQL on port `5432` and Redis on port `6379`.

### 2. Set up Python

```bash
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the server

```bash
uvicorn app.main:app --reload
```

The web UI is at [http://localhost:8000](http://localhost:8000).
Interactive API docs (Swagger) are at [http://localhost:8000/docs](http://localhost:8000/docs).

### 4. Run tests

```bash
pytest
```

---

## API reference

### Register a user

```
POST /register?email=you@example.com
```

Returns an `api_key`. You need this for all write operations.

### Shorten a URL

```
POST /shorten?long_url=https://example.com/some-long-path
```

**Headers:**

| Header | Required | Purpose |
|--------|----------|---------|
| `api-key` | Yes | Your API key from `/register` |
| `idempotency-key` | No | Prevents duplicate short codes on retries |

**Response:**

```json
{
  "short_code": "aB3xYz",
  "long_url": "https://example.com/some-long-path",
  "created_at": "2026-08-10T12:00:00"
}
```

### Redirect

```
GET /{short_code}
```

302 redirect to the original URL. The first lookup hits Postgres; every
subsequent one is served from Redis cache.

### Health check

```
GET /health
```

Returns `{"status": "ok"}`.

---

## Architecture

**Stack:** FastAPI · PostgreSQL · Redis · Docker

### Request flow

**Creating a short link (`POST /shorten`)**

1. Validate the API key against the `users` table
2. Check for a matching `Idempotency-Key` — if this exact request was already
   processed, return the stored result instead of creating a duplicate
3. Check the caller's rate limit (token bucket, per IP, stored in Redis)
4. Generate a random 6-character short code; check it against the database for
   collisions, retrying up to 5 times if needed
5. Save the new URL record to PostgreSQL
6. Store the result under the idempotency key for future retries
7. Return the short link

**Visiting a short link (`GET /{code}`)**

1. Check Redis for a cached long URL — if found, redirect immediately
2. On a cache miss, query PostgreSQL, then write the result into Redis for future
   requests, then redirect
3. If Redis is unreachable at any point, skip caching entirely and serve directly
   from PostgreSQL — the redirect still succeeds, just without the speed benefit
4. If the code doesn't exist, return a 404

---

## Key design decisions

**Why cache-aside instead of write-through caching?**

URL shorteners are heavily read-skewed — most links are created once but clicked
many times. Cache-aside means the cache is only populated on demand (when a link
is actually visited), avoiding the cost of caching links that may never be read
again. Write-through would cache every link immediately on creation, which wastes
cache space and write time on links nobody visits.

**Why random short codes with collision retry, instead of a sequential counter?**

A sequential counter (1, 2, 3…) never collides, but it's predictable — anyone
could estimate how many links exist or guess valid codes by incrementing a number.
Random generation avoids this, at the cost of needing collision handling, which is
implemented as a bounded retry loop (max 5 attempts) backed by a database-level
unique constraint on `short_code` as the real guarantee against duplicates.

**Why token bucket for rate limiting, instead of a fixed window counter?**

A fixed window (e.g., "max 5 requests per 10-second window") allows a burst of up
to 2× the limit right at the window boundary, since a client can send the limit at
the very end of one window and the limit again at the very start of the next. Token
bucket approaches avoid this edge case. This implementation uses a simplified,
Redis-backed fixed-window approximation rather than a continuous refill — a true
token bucket would refill gradually rather than resetting all at once.

**Why idempotency keys on link creation?**

If a client's request succeeds but the response is lost (network blip, timeout),
a naive retry would create a second, duplicate short link for the same URL. Clients
can send an `Idempotency-Key` header, and the server returns the original result for
any repeat of that key within a 5-minute window, instead of creating a new link. This
is the same pattern used by payment APIs like Stripe, where duplicate side effects
from retries are unacceptable.

**Why does the app stay up if Redis goes down?**

Redis is a performance optimization, not a source of truth — PostgreSQL is. All
Redis calls are wrapped in error handling that falls back to querying PostgreSQL
directly if Redis is unreachable, so the service degrades gracefully (slower, but
still correct) instead of failing outright.



## Project structure

```
├── app/
│   ├── main.py            # Routes and core logic
│   ├── models.py          # SQLAlchemy models (URL, User)
│   └── database.py        # DB engine, session factory, Redis client
├── tests/
│   └── test_main.py       # API tests (health, auth, shorten, redirect, rate limit, idempotency)
├── static/
│   └── index.html         # Web UI
├── docker-compose.yml     # Postgres + Redis containers
├── requirements.txt       # Python dependencies
├── pytest.ini             # Test configuration
└── readme.md
```

---

## Database schema

**urls**

| Column | Type | Notes |
|--------|------|-------|
| id | Integer | Primary key |
| short_code | String | Unique, indexed |
| long_url | String | The original URL |
| created_at | DateTime | Auto-set on creation |
| expires_at | DateTime | Nullable (not enforced yet) |

**users**

| Column | Type | Notes |
|--------|------|-------|
| id | Integer | Primary key |
| email | String | Unique |
| api_key | String | Unique, indexed |
| created_at | DateTime | Auto-set on creation |

---

In production (deployed on [Render](https://render.com)), these point to a managed
Postgres instance ([Neon](https://neon.tech)) and managed Redis instance
([Upstash](https://upstash.com)) instead.
## Configuration

Database and Redis connections are configured in `app/database.py`. Currently
hardcoded for local development:

- **Postgres:** `postgresql://postgres:postgres@localhost:5432/urlshortener`
- **Redis:** `localhost:6379`

For production, swap these with environment variables.

---

## License

MIT — see [LICENSE](LICENSE).
