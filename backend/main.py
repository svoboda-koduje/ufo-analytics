# -*- coding: utf-8 -*-
import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from dotenv import load_dotenv

from models import UfoCase

load_dotenv()

app = FastAPI(
    title="UFO / UAP Analytics API",
    description="Badatelský analytický engine pro odtajněné vládní spisy",
    version="2.2"
)

# CORS konfigurace pro komunikaci s Next.js frontendem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Chybí proměnná prostředí DATABASE_URL. Nastav ji v .env nebo na Render.com.")

# Oprava schématu pro SQLAlchemy u novějších verzí Postgresu (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic schémata pro validaci výstupů
class CaseResponse(BaseModel):
    id: str
    title: str
    date: Optional[str] = "Neznámé datum"
    location: Optional[str] = "USA / Vládní archiv"
    status: Optional[str] = "Unresolved"
    agency: Optional[str] = "Department of War"
    file_type: Optional[str] = "PDF"
    translation_snippet: Optional[str] = ""
    original_text: Optional[str] = ""
    latitude: Optional[float] = 37.2350
    longitude: Optional[float] = -115.8111
    source_url: Optional[str] = "https://www.war.gov/UFO/"

    class Config:
        from_attributes = True


@app.get("/")
def read_root():
    return {
        "status": "UFO Analytics Engine Running",
        "database": "Connected to Supabase",
        "version": "2.2"
    }


@app.get("/api/cases/", response_model=List[CaseResponse])
def get_cases(
    search: Optional[str] = Query(None, description="Hledat v názvu, lokaci nebo textu"),
    status: Optional[str] = Query(None, description="Filtr podle statusu (Resolved / Unresolved)"),
    agency: Optional[str] = Query(None, description="Filtr podle agentury"),
    file_type: Optional[str] = Query(None, description="Filtr podle typu souboru (PDF, MP4, JPG)"),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(UfoCase)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                UfoCase.title.ilike(search_filter),
                UfoCase.location.ilike(search_filter),
                UfoCase.case_id.ilike(search_filter),
                UfoCase.translation_snippet.ilike(search_filter)
            )
        )

    if status and status.lower() != "all":
        query = query.filter(UfoCase.status.ilike(status))

    if hasattr(UfoCase, "agency") and agency and agency.lower() != "all":
        query = query.filter(UfoCase.agency.ilike(agency))

    if hasattr(UfoCase, "file_type") and file_type and file_type.lower() != "all":
        query = query.filter(UfoCase.file_type.ilike(file_type))

    cases = query.offset(offset).limit(limit).all()

    return [
        CaseResponse(
            id=c.case_id,
            title=c.title,
            date=c.date or "Neznámé datum",
            location=c.location or "USA / Vládní archiv",
            status=c.status or "Unresolved",
            agency=getattr(c, "agency", "Department of War"),
            file_type=getattr(c, "file_type", "PDF"),
            translation_snippet=c.translation_snippet or "Záznam vykazuje anomální letovou dynamiku.",
            original_text=c.original_text or "Archival document loaded.",
            latitude=c.latitude if c.latitude is not None else 37.2350,
            longitude=c.longitude if c.longitude is not None else -115.8111,
            source_url=c.source_url or "https://www.war.gov/UFO/"
        )
        for c in cases
    ]


@app.get("/api/cases/{case_id}", response_model=CaseResponse)
def get_case_detail(case_id: str, db: Session = Depends(get_db)):
    c = db.query(UfoCase).filter(UfoCase.case_id == case_id).first()
    if not c:
        raise HTTPException(status_code=404, detail=f"Případ {case_id} nebyl nalezen.")
    
    return CaseResponse(
        id=c.case_id,
        title=c.title,
        date=c.date or "Neznámé datum",
        location=c.location or "USA / Vládní archiv",
        status=c.status or "Unresolved",
        agency=getattr(c, "agency", "Department of War"),
        file_type=getattr(c, "file_type", "PDF"),
        translation_snippet=c.translation_snippet or "",
        original_text=c.original_text or "",
        latitude=c.latitude if c.latitude is not None else 37.2350,
        longitude=c.longitude if c.longitude is not None else -115.8111,
        source_url=c.source_url or "https://www.war.gov/UFO/"
    )


@app.get("/api/stats/")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(UfoCase).count()
    unresolved = db.query(UfoCase).filter(UfoCase.status == "Unresolved").count()
    resolved = db.query(UfoCase).filter(UfoCase.status == "Resolved").count()
    
    unresolved_pct = round((unresolved / total * 100), 1) if total > 0 else 0.0
    resolved_pct = round((resolved / total * 100), 1) if total > 0 else 0.0

    return {
        "total_cases": total,
        "resolved_cases": resolved,
        "unresolved_cases": unresolved,
        "unresolved_percentage": unresolved_pct,
        "resolved_percentage": resolved_pct
    }
