# -*- coding: utf-8 -*-
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import UfoCase
from ingestion_engine import process_incoming_files
from scraper import scrape_ufo_portal

app = FastAPI(
    title="UFO Analytics API", 
    version="3.2",
    description="Badatelský analytický nástroj pro vyhodnocování UAP případů z war.gov/UFO a AARO."
)

# Povolení CORS pro bezproblémovou komunikaci s frontendem na Renderu
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    """
    Vrací základní stavový přehled analytického enginu v low-budget režimu.
    """
    return {
        "status": "UFO Analytics Engine Running (Supabase Connected)",
        "mode": "Low-Budget Autonomous Pipeline",
        "version": "3.2"
    }

@app.get("/api/cases/")
def get_cases(db: Session = Depends(get_db)):
    """
    Vrací reálné UAP případy z cloudové databáze Supabase včetně GIS souřadnic pro mapu.
    """
    try:
        cases = db.query(UfoCase).all()
        return [
            {
                "id": c.case_id,
                "title": c.title,
                "date": c.date,
                "location": c.location,
                "latitude": c.latitude,
                "longitude": c.longitude,
                "status": c.status,
                "translation_snippet": c.translation_snippet,
                "original_text": c.original_text,
                "source_url": c.source_url
            }
            for c in cases
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba databázové vrstvy: {str(e)}")

@app.post("/api/ingest-folder/")
def trigger_folder_ingestion():
    """
    Spustí lokální ingesční modul, který zkontroluje složku incoming_data
    a automaticky zpracuje nové PDF spisy, obrázky a videa do Supabase.
    """
    try:
        process_incoming_files()
        return {"status": "Ingestion process completed successfully in low-budget mode"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/sync-war-gov/")
@app.post("/api/sync-war-gov/")
def sync_and_analyze_war_gov():
    """
    1. Spustí web scraper pro automatické stažení nových materiálů z war.gov/UFO.
    2. Spustí ingesční modul pro OCR, parsování a uložení do Supabase.
    Podporuje GET i POST pro snadné testování z prohlížeče.
    """
    try:
        scrape_result = scrape_ufo_portal()
        process_incoming_files()
        return {
            "status": "Sync and ingestion pipeline executed successfully",
            "scrape_details": scrape_result
        }
    except Exception as e:
        return {"error": str(e)}
