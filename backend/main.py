# -*- coding: utf-8 -*-
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import UfoCase
import os

app = FastAPI(title="UFO Analytics API", version="2.0")

# Povolení CORS pro komunikaci s frontendem na Renderu
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ.get("DATABASE_URL") or "postgresql://postgres:postgres.qbvhzjzbjihwjbfptrn:VvXCTpPGW8RcxG@db.qbvhzjzbjihwjbfptrn.supabase.co:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"status": "UFO Analytics Engine Running", "database": "Connected to Supabase"}

@app.get("/api/cases/")
def get_cases(db: Session = Depends(get_db)):
    """Vrací všech 356+ reálných případů z databáze pro mapu a katalog."""
    cases = db.query(UfoCase).all()
    return [
        {
            "id": c.case_id,
            "title": c.title,
            "date": c.date,
            "location": c.location,
            "status": c.status,
            "translation_snippet": c.translation_snippet,
            "latitude": c.latitude or 37.2350,
            "longitude": c.longitude or -115.8111,
            "source_url": c.source_url
        }
        for c in cases
    ]

@app.get("/api/stats/")
def get_stats(db: Session = Depends(get_db)):
    """Vypočítá poměr vyřešených a nevysvětlených případů pro analytický přehled."""
    total = db.query(UfoCase).count()
    unresolved = db.query(UfoCase).filter(UfoCase.status == "Unresolved").count()
    resolved = total - unresolved
    unresolved_pct = round((unresolved / total * 100) if total > 0 else 0, 1)
    
    return {
        "total_cases": total,
        "resolved_cases": resolved,
        "unresolved_cases": unresolved,
        "unresolved_percentage": unresolved_pct,
        "resolved_percentage": round(100 - unresolved_pct, 1)
    }
