from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import UfoCase
from ingestion_engine import process_incoming_files

app = FastAPI(title="UFO Analytics API", version="3.0")

# Povolení CORS pro bezproblémovou komunikaci s frontendem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "UFO Analytics Engine Running (Supabase Connected)"}

@app.get("/api/cases/")
def get_cases(db: Session = Depends(get_db)):
    """
    Vrací reálné UAP případy z cloudové databáze Supabase včetně GIS souřadnic.
    """
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

@app.post("/api/ingest-folder/")
def trigger_folder_ingestion():
    """
    Spustí ingesční modul, který zkontroluje složku incoming_data
    a automaticky zpracuje nové PDF, obrázky a videa do Supabase.
    """
    try:
        process_incoming_files()
        return {"status": "Ingestion process completed successfully"}
    except Exception as e:
        return {"error": str(e)}