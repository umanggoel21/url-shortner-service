from fastapi import FastAPI
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import URL
import random
import string
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

@app.get("/{code}")
def redirect_to_url(code: str, db: Session = Depends(get_db)):
    url_entry = db.query(URL).filter(URL.short_code == code).first()

    if not url_entry:
        raise HTTPException(status_code=404, detail="Short URL not found")

    return RedirectResponse(url=url_entry.long_url, status_code=302)

def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=length))


@app.post("/shorten")
def shorten_url(long_url: str, db: Session = Depends(get_db)):
    short_code = generate_short_code()

    new_url = URL(short_code=short_code, long_url=long_url)
    db.add(new_url)
    db.commit()
    db.refresh(new_url)

    return {
        "short_code": new_url.short_code,
        "long_url": new_url.long_url,
        "created_at": new_url.created_at
    }
@app.get("/health")
def health_check():
    return {"status": "ok"}