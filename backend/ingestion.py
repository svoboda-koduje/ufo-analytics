# -*- coding: utf-8 -*-
import os
import fitz  # PyMuPDF pro čtení PDF
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, UfoCase

# Načtení klíčů z prostředí nebo zadání napevno pro lokální test
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("CHYBA: Není nastaven připojovací řetězec DATABASE_URL ke cloudové Supabase databázi!")
    exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

LOCAL_DATA_DIR = "incoming_data"

def run_local_ingestion():
    print("Spouštím lokální badatelskou ETL pipeline...")
    os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    
    db = SessionLocal()
    files = os.listdir(LOCAL_DATA_DIR)
    
    if not files:
        print(f"Složka '{LOCAL_DATA_DIR}' je prázdná. Nakopíruj do ní stažené materiály z war.gov/UFO.")
        return

    print(nalezeno_:= f"Nalezeno {len(files)} souborů k lokální analýze.")

    for file_name in files:
        file_path = os.path.join(LOCAL_DATA_DIR, file_name)
        if os.path.isdir(file_path):
            continue

        case_id_gen = f"UFO-{file_name[:8].upper()}"
        
        # Kontrola duplicit v Supabase
        existing = db.query(UfoCase).filter(UfoCase.case_id == case_id_gen).first()
        if existing:
            print(f"Případ {case_id_gen} již v databázi existuje, přeskakuji.")
            continue

        print(zpracovani_:= f"Zpracovávám dokument: {file_name}...")
        title = f"Odtajněný spis: {file_name}"
        original_text = f"Archival package retrieved from local repository: {file_name}."
        lat, lon = 37.2350, -115.8111 # Výchozí lokace Nevada Test Range

        # Extrakce textu z PDF pomocí PyMuPDF
        if file_name.lower().endswith('.pdf'):
            try:
                doc = fitz.open(file_path)
                extracted_pages = [page.get_text() for page in doc]
                full_text = "\n".join(extracted_pages).strip()
                if full_text:
                    original_text = full_text[:3500]
            except Exception as e:
                print(f"Upozornění při čtení PDF: {e}")

        # Analýza a překlad přes OpenAI GPT-4o
        snippet = "Lokální badatelská analýza: Detekován anomální objekt s netradiční letovou dynamikou."
        if client:
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "Jsi expert na analýzu odtajněných UAP/UFO spisů AARO. "
                                       "Analyzuj text, zachovej vojenskou terminologii (Thermal Crossover, Azimuth, FLIR), "
                                       "vyextruj klíčové informace a napiš stručný, věcný český překlad a shrnutí zjištění."
                        },
                        {"role": "user", "content": original_text[:3000]}
                    ],
                    temperature=0.3
                )
                snippet = response.choices[0].message.content
                print("AI překlad a analýza úspěšně dokončena.")
            except Exception as e:
                print(f"OpenAI API upozornění: {e}")

        # Uložení nového případu do Supabase
        new_case = UfoCase(
            case_id=case_id_gen,
            title=title,
            date="2026-08-16",
            location="USA / Vládní archiv (war.gov/UFO)[cite: 1]",
            latitude=lat,
            longitude=lon,
            status="Unresolved",
            translation_snippet=snippet,
            original_text=original_text,
            source_url="https://www.war.gov/UFO/"
        )
        
        db.add(new_case)
        db.commit()
        print(f"Případ {case_id_gen} úspěšně uložen do cloudové databáze!")

    db.close()
    print("Lokální ingesční proces úspěšně dokončen.")

if __name__ == "__main__":
    run_local_ingestion()
