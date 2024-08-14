# main.py
import os
import logging
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
import string
import random

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TODO: Move these constants to a config file
BASE_URL = "http://localhost:8000"
SHORT_CODE_LENGTH = 6

# Database configuration
# TODO: Use environment variables for sensitive information
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:rocketmonkey12@localhost/url_shortener")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, index=True)
    short_code = Column(String, unique=True, index=True)

class URLBase(BaseModel):
    url: str

app = FastAPI()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_short_code(length: int = SHORT_CODE_LENGTH) -> str:
    """Generate a random short code of specified length."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def create_short_url(db: Session, original_url: str) -> str:
    """Create a short URL and store it in the database."""
    while True:
        short_code = generate_short_code()
        if not db.query(URL).filter(URL.short_code == short_code).first():
            break
    
    db_url = URL(original_url=original_url, short_code=short_code)
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    return short_code

@app.post("/shorten")
def shorten_url(url_base: URLBase, db: Session = Depends(get_db)):
    """Endpoint to create a shortened URL."""
    try:
        short_code = create_short_url(db, url_base.url)
        return {"shortened_url": f"{BASE_URL}/{short_code}"}
    except Exception as e:
        logger.error(f"Error shortening URL: {str(e)}")
        raise HTTPException(status_code=500, detail="Error shortening URL")

@app.get("/{short_code}")
def redirect_to_url(short_code: str, db: Session = Depends(get_db)):
    """Endpoint to redirect to the original URL."""
    db_url = db.query(URL).filter(URL.short_code == short_code).first()
    if db_url is None:
        raise HTTPException(status_code=404, detail="URL not found")
    return {"url": db_url.original_url}

# TODO: Implement a cleanup function to remove old/unused URLs
# TODO: Add rate limiting to prevent abuse
# TODO: Implement user authentication for premium features

if __name__ == "__main__":
    import uvicorn
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Run the application
    uvicorn.run(app, host="0.0.0.0", port=8000)