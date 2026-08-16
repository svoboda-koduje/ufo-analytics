# -*- coding: utf-8 -*-
import os
import sys

print("==================================================")
print(" SPUŠTĚNÍ DÁVKOVÉ ETL INGESCE VŠECH UAP SOUBORŮ ")
print("==================================================")

# Absolutní cesta ke složce incoming_data na tvém disku
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(BASE_DIR, "incoming_data")
print(f"Složka s daty: {LOCAL_DATA_DIR}")

# 1. Supabase připojení přes Session pooler (port 6543 pro spolehlivý průchod sítí)
DATABASE_URL = "postgresql://postgres.qbvhzjzbxjihwjbfptrn:UfoAnalytics2026@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"

print("Testuji připojení k databázi Supabase...")
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, UfoCase
    
    # Přidán timeout pro stabilnější navázání spojení
    engine = create_engine(DATABASE_URL, connect_args={'connect_timeout': 20})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    conn = engine.connect()
    conn.close()
    print("[OK] Připojení k Supabase databázi úspěšně navázáno!")
except Exception as e:
    print(f"\n[CHYBA PŘIPOJENÍ] Nepodařilo se připojit k databázi: {e}")
    print("Zkontroluj prosím, zda máš v URL správně zapsané heslo (bez závorek []) a zda nepoužíváš blokující VPN.")
    sys.exit(1)

# 2. Načtení modulu PyMuPDF pro čtení PDF spisů
try:
    import pymupdf as fitz
    has_fitz = True
    print("[OK] Modul PyMuPDF připraven.")
except ImportError:
    try:
        import fitz
        has_fitz = True
        print("[OK] Modul PyMuPDF (fitz) připraven.")
    except ImportError:
        has_fitz = False
        print("[INFO] PyMuPDF není k dispozici, PDF se zpracují bez textu.")

# 3. Inicializace OpenAI klienta (využije tvé kredity)
OPENAI_API_KEY = "sk-proj-jWX1RltluAGCed2ckSjcV-19Pzg5sKcTfwib2SubJughVlTZOS0X0URximkLQI3R6wQ2QaT3B1bkFJSiqFF121cubnKc04T98zXSZHp4GRY8FA11rxdj9_JZupcgimza4bd7bEKpXFd3hlermk_rZQA"
client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        print("[OK] OpenAI klient inicializován pro AI překlady a analýzu.")
    except Exception as e:
        print(f"[INFO] OpenAI nelze inicializovat: {e}")

def run_batch_ingestion():
    if not os.path.exists(LOCAL_DATA_DIR):
        print(f"[CHYBA] Složka '{LOCAL_DATA_DIR}' neexistuje!")
        return

    db = SessionLocal()
    files = os.listdir(LOCAL_DATA_DIR)
    total_files = len(files)
    print(f"Nalezeno celkem položek ke zpracování: {total_files}")

    if total_files == 0:
        print("[VAROVÁNÍ] Složka 'incoming_data' je prázdná!")
        db.close()
        return

    success_count = 0
    skipped_count = 0

    for index, file_name in enumerate(files, start=1):
        file_path = os.path.join(LOCAL_DATA_DIR, file_name)
        if os.path.isdir(file_path):
            continue

        clean_name = file_name.replace('.', '-').replace('_', '-')[:30].upper()
        case_id_gen = f"UAP-{clean_name}"

        # Kontrola duplicit v Supabase
        existing = db.query(UfoCase).filter(UfoCase.case_id == case_id_gen).first()
        if existing:
            skipped_count += 1
            continue

        print(f"[{index}/{total_files}] Zpracovávám: {file_name}...")
        title = f"Odtajněný spis AARO/NARA: {file_name}"
        original_text = f"Archival package retrieved from local repository: {file_name}."
        lat, lon = 37.2350, -115.8111  # Výchozí geolokace (Nevada Test Range / Area 51)

        # Extrakce textu z PDF
        if file_name.lower().endswith('.pdf') and has_fitz:
            try:
                doc = fitz.open(file_path)
                extracted_pages = [page.get_text() for page in doc]
                full_text = "\n".join(extracted_pages).strip()
                if full_text:
                    original_text = full_text[:3500]
            except Exception as e:
                print(f"   [VAROVÁNÍ] Chyba při čtení PDF: {e}")

        # AI analýza a odborný překlad přes GPT-4o
        snippet = f"Badatelský přehled (Lokální ETL): Materiál {file_name} byl zaevidován a připraven k analýze."
        if client:
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "Jsi expert na analýzu odtajněných UAP/UFO spisů AARO. "
                                       "Analyzuj text, zachovej vojenskou terminologii (Thermal Crossover, Azimuth, FLIR, AGL), "
                                       "vyextruj klíčové informace a napiš stručný, věcný český překlad a shrnutí zjištění."
                        },
                        {"role": "user", "content": original_text[:2500]}
                    ],
                    temperature=0.3
                )
                snippet = response.choices[0].message.content
            except Exception as e:
                pass

        # Uložení záznamu do databáze
        new_case = UfoCase(
            case_id=case_id_gen,
            title=title,
            date="2026-08-16",
            location="USA / Vládní archiv (war.gov/UFO)",
            latitude=lat,
            longitude=lon,
            status="Unresolved",
            translation_snippet=snippet,
            original_text=original_text,
            source_url="https://www.war.gov/UFO/[cite: 1]"
        )

        try:
            db.add(new_case)
            db.commit()
            success_count += 1
            print(f"   [OK] Uloženo do Supabase jako {case_id_gen}")
        except Exception as db_err:
            db.rollback()
            print(f"   [CHYBA ZÁPISU] Nelze uložit do DB: {db_err}")

    db.close()
    print("==================================================")
    print(f" DÁVKOVÉ ZPRACOVÁNÍ DOKONČENO!")
    print(f" Úspěšně uloženo nových případů: {success_count}")
    print(f" Přeskočeno (již v DB): {skipped_count}")
    print("==================================================")

if __name__ == "__main__":
    run_batch_ingestion()
