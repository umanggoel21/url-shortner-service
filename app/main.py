from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal, redis_client
from app.models import URL
import random
import string
import redis


app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=length))

def is_rate_limited(identifier: str, max_tokens: int = 5, refill_seconds: int = 10):
    key = f"ratelimit:{identifier}"
    current = redis_client.get(key)

    if current is None:
        redis_client.set(key, max_tokens - 1, ex=refill_seconds)
        return False

    remaining = int(current)
    if remaining <= 0:
        return True

    redis_client.decrby(key, 1)
    return False

@app.get("/health")
def health_check():
    return {"status": "ok"}



@app.post("/shorten")
def shorten_url(long_url: str, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host

    if is_rate_limited(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests, please try again shortly")

    max_attempts = 5
    short_code = None

    for attempt in range(max_attempts):
        candidate = generate_short_code()
        existing = db.query(URL).filter(URL.short_code == candidate).first()

        if not existing:
            short_code = candidate
            break
        else:
            print(f"Collision on attempt {attempt+1}: {candidate} already exists, retrying...")

    if short_code is None:
        raise HTTPException(status_code=500, detail="Could not generate a unique short code, please try again")

    new_url = URL(short_code=short_code, long_url=long_url)
    db.add(new_url)
    db.commit()
    db.refresh(new_url)

    return {
        "short_code": new_url.short_code,
        "long_url": new_url.long_url,
        "created_at": new_url.created_at
    }

@app.get("/{code}")
def redirect_to_url(code: str, db: Session = Depends(get_db)):
    try:
        cached_url = redis_client.get(code)
        if cached_url:
            print(f"Cache HIT for {code}")
            return RedirectResponse(url=cached_url, status_code=302)
    except redis.exceptions.ConnectionError:
        print("Redis unavailable, falling back to database")

    print(f"Cache MISS for {code}, checking database")
    url_entry = db.query(URL).filter(URL.short_code == code).first()

    if not url_entry:
        raise HTTPException(status_code=404, detail="Short URL not found")

    try:
        redis_client.set(code, url_entry.long_url)
    except redis.exceptions.ConnectionError:
        print("Redis unavailable, skipping cache write")

    return RedirectResponse(url=url_entry.long_url, status_code=302)