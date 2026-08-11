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

## How it works

1. **Registration** — A user signs up with an email and receives an API key.
2. **Shortening** — An authenticated request sends a long URL. The server generates
   a random 6-character code, checks for collisions (up to 5 retries), and stores
   the mapping in Postgres.
3. **Redirecting** — When someone visits `/{code}`, the server checks Redis first.
   On a cache miss, it falls back to Postgres and writes the result back to Redis
   for next time.
4. **Rate limiting** — A token-bucket algorithm in Redis allows 5 requests per 10
   seconds per IP. Requests beyond that get a `429`.
5. **Idempotency** — If a client sends the same `idempotency-key` header within 5
   minutes, the server returns the original response instead of creating a duplicate
   entry.

---

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

## Configuration

Database and Redis connections are configured in `app/database.py`. Currently
hardcoded for local development:

- **Postgres:** `postgresql://postgres:postgres@localhost:5432/urlshortener`
- **Redis:** `localhost:6379`

For production, swap these with environment variables.

---

## License

MIT — see [LICENSE](LICENSE).
