import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import redis

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/urlshortener")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)