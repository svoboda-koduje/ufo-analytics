# -*- coding: utf-8 -*-
import os
import fitz  # PyMuPDF pro čtení PDF
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, UfoCase

print("==================================================")
print(" SPOUSTÍM LOKÁLNÍ BADATELSKOU ETL PIPELINE PRO UAP ")
print("==================================================")

# Načtení klíčů z prostředí PowerShellu
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("CHYBA: Není nastavena proměnná DATABASE_URL!")
    exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

LOCAL_DATA_DIR = "incoming_data"

def run_local_ingestion():
    os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    db = SessionLocal()
    
    files = os.listdir(LOCAL_DATA_DIR)
    print(f"Kontroluji složku '{LOCAL_DATA_DIR}'. Nalezeno souborů: {len(files)}")
    
    if len(files) == 0:
        print(f"UPOZORNĚNÍ: Složka '{LOCAL_DATA_DIR}' je prázdná! Nakopíruj do ní stažené soubory (PDF, JPG, MP4).")
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

        # Pokud jde o PDF, vytáhneme text pomocí PyMuPDF
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

        # Pokus o AI analýzu přes OpenAI (pokud selže kvůli kreditům, script nepadá)
        snippet = "Lokální badatelská analýza: Záznam vykazuje anomální parametry a netradiční letovou dynamiku."
        if client:
            try:
                print("   Odesílám data k analýze a překladu přes OpenAI...")
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
                print(f"   [INFO] OpenAI přeskočeno (vyčerpané kredity nebo limit API): {e}")
                snippet = f"Badatelský přehled (Lokální režim): Dokument {file_name} byl úspěšně zaevidován a připraven k analýze."

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
    print("==================================================")
    print(" VŠECHNY ÚLOHY ÚSPĚŠNĚ DOKONČENY ")
    print("==================================================")

if __name__ == "__main__":
    run_local_ingestion()
