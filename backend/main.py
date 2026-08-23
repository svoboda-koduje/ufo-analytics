# -*- coding: utf-8 -*-
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

from models import UfoCase, Base

load_dotenv()

app = FastAPI(title="UFO / UAP Analytics API", version="2.5")

# CORS konfigurace
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ.get("DATABASE_URL") or "postgresql://postgres.qbvhzjzbjihwjbfptrn:VvXCTpPGW8RcxG@db.qbvhzjzbjihwjbfptrn.supabase.co:5432/postgres"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"status": "UFO Analytics Engine Online", "database": "Connected"}

@app.get("/api/cases")
@app.get("/api/cases/")
def get_cases(db: Session = Depends(get_db)):
    try:
        cases = db.query(UfoCase).order_by(UfoCase.id.asc()).all()
        return [
            {
                "id": c.id,
                "case_id": c.case_id,
                "title": c.title,
                "asset_file_name": c.asset_file_name or "",
                "file_type": c.file_type or "PDF",
                "agency": c.agency or "Department of War",
                "release_tag": c.release_tag or "",
                "date": c.incident_date or "Neznámé datum",
                "incident_date": c.incident_date or "Neznámé datum",
                "location": c.location or "USA / Vládní archiv",
                "latitude": c.latitude if c.latitude is not None else 38.8951,
                "longitude": c.longitude if c.longitude is not None else -77.0364,
                "status": c.status or "Unresolved",
                "original_text": c.original_text or "Originální text nebyl extrahován.",
                "translation_snippet": c.czech_translation or "Analýza nebyla provedena.",
                "czech_translation": c.czech_translation or "Analýza nebyla provedena.",
                "search_url": c.search_url or f"https://www.war.gov/UFO/?search={c.asset_file_name}"
            }
            for c in cases
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při čtení z databáze: {str(e)}")
