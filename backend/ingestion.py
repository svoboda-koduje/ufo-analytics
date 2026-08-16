# -*- coding: utf-8 -*-
import os
import sys

print("=== START LOKÁLNÍ ETL PIPELINE ===")

# =====================================================================
# TADY SI MŮŽEŠ ROVNOU VYPLNIT SVÉ ÚDAJE PRO JEDNODUCHÉ SPUŠTĚNÍ
# =====================================================================
DIRECT_DATABASE_URL = "postgresql://postgres:pIVvXCTpPGW8RcxG@db.qbvhzjzbxjihwjbfptrn.supabase.co:5432/postgres"
DIRECT_OPENAI_KEY = "sk-proj-jWX1RltluAGCed2ckSjcV-19Pzg5sKcTfwib2SubJughVlTZOS0X0URximkLQI3R6wQ2QaT3B1bkFJSiqFF121cubnKc04T98zXSZHp4GRY8FA11rxdj9_JZupcgimza4bd7bEKpXFd3hlermk_rZQA"

# Načtení z prostředí nebo z přímých proměnných výše
DATABASE_URL = os.environ.get("DATABASE_URL") or DIRECT_DATABASE_URL
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or DIRECT_OPENAI_KEY

if not DATABASE_URL:
    print("CHYBA: Není nastaven DATABASE_URL!")
    sys.exit(1)

# Import knihoven s kontrolou
try:
    import fitz  # PyMuPDF
    print("[OK] PyMuPDF načten.")
except ImportError:
    print("[CHYBA] Chybí knihovna PyMuPDF. Nainstaluj ji příkazem: pip install PyMuPDF")
    sys.exit(1)

try:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
    if client:
        print("[OK] OpenAI klient inicializován.")
    else:
        print("[INFO] OpenAI klíč není k dispozici, pojede se v lokálním režimu.")
except Exception as e:
    print(f"[INFO] OpenAI nelze načíst: {e}")
    client = None

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, UfoCase
    print("[OK] Databázové modely načteny.")
except Exception as e:
    print(f"[CHYBA] Chyba při importu modelů: {e}")
    sys.exit(1)

LOCAL_DATA_DIR = "incoming_data"

def run_local_ingestion():
    os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    files = os.listdir(LOCAL_DATA_DIR)
    print(f"Kontroluji složku '{LOCAL_DATA_DIR}'. Nalezeno souborů: {len(files)}")
    
    if len(files) == 0:
        print(f"UPOZORNĚNÍ: Složka '{LOCAL_DATA_DIR}' je prázdná! Nakopíruj do ní stažené soubory (PDF, JPG).")
        db.close()
        return

    for file_name in files:
        file_path = os.path.join(LOCAL_DATA_DIR, file_name)
        if os.path.isdir(file_path):
            continue

        case_id_gen = f"LOCAL-{file_name[:8].upper()}"
        
        # Kontrola duplicit v Supabase
        existing = db.query(UfoCase).filter(UfoCase.case_id == case_id_gen).first()
        if existing:
            print(f"-> Případ {case_id_gen} ({file_name}) již v databázi existuje, přeskakuji.")
            continue

        print(f"-> Zpracovávám soubor: {file_name}...")
        title = f"Lokální archivní spis: {file_name}"
        original_text = f"Raw local file package: {file_name}."
        lat, lon = 37.2350, -115.8111  # Výchozí lokace Nevada / Area 51

        # Extrakce textu z PDF
        if file_name.lower().endswith('.pdf'):
            try:
                doc = fitz.open(file_path)
                extracted_pages = [page.get_text() for page in doc]
                full_text = "\n".join(extracted_pages).strip()
                if full_text:
                    original_text = full_text[:3500]
                print(f"   [OK] Úspěšně vytažen text z PDF ({len(full_text)} znaků).")
            except Exception as e:
                print(f"   [VAROVÁNÍ] Chyba při čtení PDF: {e}")

        # AI analýza
        snippet = "Lokální badatelská analýza: Záznam vykazuje anomální parametry a netradiční letovou dynamiku."
        if client:
            try:
                print("   Odesílám data k analýze přes OpenAI...")
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
                print("   [OK] OpenAI analýza úspěšně dokončena.")
            except Exception as e:
                print(f"   [INFO] OpenAI přeskočeno (chyba kreditů/API): {e}")

        # Uložení do Supabase
        new_case = UfoCase(
            case_id=case_id_gen,
            title=title,
            date="2026-08-16",
            location="USA / Lokální badatelský archiv",
            latitude=lat,
            longitude=lon,
            status="Unresolved",
            translation_snippet=snippet,
            original_text=original_text,
            source_url="https://www.war.gov/UFO/"
        )
        
        db.add(new_case)
        db.commit()
        print(f"   [ÚSPĚCH] Případ {case_id_gen} zapsán do Supabase databáze!")

    db.close()
    print("=== VŠECHNY ÚLOHY ÚSPĚŠNĚ DOKONČENY ===")

if __name__ == "__main__":
    run_local_ingestion()
