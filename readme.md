# URL Shortener Service

A URL Shortener service with API key authentication, Redis caching for fast redirects, rate limiting, and idempotency support.

## Stack

- **FastAPI** — API framework
- **PostgreSQL** — stores URLs and users
- **Redis** — caches redirects + handles rate limiting
- **SQLAlchemy** — ORM
- **Docker Compose** — runs Postgres and Redis locally

## Quick Start

### 1. Start the databases

```bash
docker compose up -d
```

This starts PostgreSQL (port 5432) and Redis (port 6379).

### 2. Set up Python

```bash
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install fastapi uvicorn sqlalchemy psycopg2-binary redis
```

### 3. Run the server

```bash
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) — you'll see the web UI.

Interactive API docs are at [http://localhost:8000/docs](http://localhost:8000/docs).

## API

### Register a user

```
POST /register?email=you@example.com
```

Returns an `api_key`. You'll need this for all other requests.

### Shorten a URL

```
POST /shorten?long_url=https://example.com/some-long-path
```

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `api-key` | Yes | Your API key from `/register` |
| `idempotency-key` | No | Prevents duplicate short codes for the same request |

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

Redirects (302) to the original URL. Cached in Redis after the first lookup.

### Health check

```
GET /health
```

Returns `{"status": "ok"}`.

## How it works

1. User registers with an email → gets an API key
2. Authenticated user sends a long URL → server generates a random 6-char code, stores it in Postgres
3. Anyone visits `/{code}` → server checks Redis cache first, falls back to Postgres, then redirects
4. Rate limiting (token bucket in Redis): 5 requests per 10 seconds per IP
5. Idempotency: same `idempotency-key` header within 5 minutes returns the cached response instead of creating a duplicate

## Project Structure

```
├── app/
│   ├── main.py          # Routes and business logic
│   ├── models.py        # SQLAlchemy models (URL, User)
│   └── database.py      # DB engine, session, Redis client
├── static/
│   └── index.html       # Web UI
├── docker-compose.yml   # Postgres + Redis
└── readme.md
```

## Database Schema

**urls**

| Column | Type | Notes |
|--------|------|-------|
| id | Integer | Primary key |
| short_code | String | Unique, indexed |
| long_url | String | The original URL |
| created_at | DateTime | Auto-set |
| expires_at | DateTime | Nullable (not enforced yet) |

**users**

| Column | Type | Notes |
|--------|------|-------|
| id | Integer | Primary key |
| email | String | Unique |
| api_key | String | Unique, indexed |
| created_at | DateTime | Auto-set |

## Configuration

Database and Redis connections are hardcoded in `app/database.py` for local development:

- Postgres: `postgresql://postgres:postgres@localhost:5432/urlshortener`
- Redis: `localhost:6379`

To change these for production, update `database.py` or swap in environment variables.

## License

MIT — see [LICENSE](LICENSE).
