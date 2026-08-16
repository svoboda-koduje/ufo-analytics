# -*- coding: utf-8 -*-
import os
import sys

print("==================================================")
print(" SPUŠTĚNÍ LOKÁLNÍ ETL INGESCE VŠECH SOUBORŮ ")
print("==================================================")

# Absolutní cesta ke složce incoming_data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(BASE_DIR, "incoming_data")
print(f"Složka s daty: {LOCAL_DATA_DIR}")

# Supabase připojení (používáme přímý connection string; v případě potíží zkontroluj aktivní projekt v Supabase)
DATABASE_URL = "postgresql://postgres:postgres.qbvhzjzbjihwjbfptrn:VvXCTpPGW8RcxG@db.qbvhzjzbjihwjbfptrn.supabase.co:5432/postgres"

print("1. Testuji připojení k databázi Supabase...")
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, UfoCase
    
    engine = create_engine(DATABASE_URL, connect_args={'connect_timeout': 10})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Rychlý pokus o otevření spojení
    connection = engine.connect()
    connection.close()
    print("[OK] Připojení k Supabase databázi úspěšně navázáno!")
except Exception as e:
    print(f"\n[CHYBA PŘIPOJENÍ] Nepodařilo se připojit k Supabase[cite: 1]:")
    print(f"Detail: {e}")
    print("\nPROSÍM ZKONTROLUJ:")
    print("1. Zda máš zapnutý internet / zda není aktivní blokující VPN.")
    print("2. Zda tvůj projekt na Supabase (ufo-analytics-db) není v dashboardu uspaný.")
    sys.exit(1)

# Pokus o načtení PyMuPDF (pymupdf) pro PDF
try:
    import pymupdf as fitz
    has_fitz = True
    print("[OK] Modul PyMuPDF pro čtení PDF připraven.")
except ImportError:
    try:
        import fitz  # Starší import pro kompatibilitu
        has_fitz = True
        print("[OK] Modul PyMuPDF (fitz) připraven.")
    except ImportError:
        has_fitz = False
        print("[INFO] PyMuPDF není nainstalován, PDF se uloží bez extrakce textu.")

def run_ingestion():
    if not os.path.exists(LOCAL_DATA_DIR):
        print(f"[CHYBA] Složka '{LOCAL_DATA_DIR}' neexistuje!")
        return

    db = SessionLocal()
    files = os.listdir(LOCAL_DATA_DIR)
    print(f"Nalezeno celkem položek ve složce: {len(files)}")

    processed_count = 0
    for file_name in files:
        file_path = os.path.join(LOCAL_DATA_DIR, file_name)
        if os.path.isdir(file_path):
            continue

        # Vygenerování jedinečného ID na základě názvu souboru
        clean_name = file_name.replace('.', '-').replace('_', '-')[:35].upper()
        case_id_gen = f"UAP-{clean_name}"

        # Kontrola, zda už případ v Supabase není
        existing = db.query(UfoCase).filter(UfoCase.case_id == case_id_gen).first()
        if existing:
            continue

        print(f"-> Zpracovávám: {file_name}")
        title = f"Archivní spis / záznam: {file_name}"
        original_text = f"Materiál z lokálního disku: {file_name}"
        lat, lon = 37.2350, -115.8111  # Výchozí geolokace (Nevada / Test Range)

        # Extrakce textu, pokud jde o PDF
        if file_name.lower().endswith('.pdf') and has_fitz:
            try:
                doc = fitz.open(file_path)
                extracted_pages = [page.get_text() for page in doc]
                full_text = "\n".join(extracted_pages).strip()
                if full_text:
                    original_text = full_text[:3500]
                print(f"   [OK] Text z PDF úspěšně vytažen ({len(full_text)} znaků).")
            except Exception as e:
                print(f"   [VAROVÁNÍ] Chyba při čtení PDF: {e}")

        # Vytvoření badatelského shrnutí
        snippet = f"Lokální badatelská analýza souboru {file_name}: Odtajněný materiál obsahující anomální telemetrické či textové záznamy."

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
            source_url="https://www.war.gov/UFO/"
        )

        db.add(new_case)
        db.commit()
        processed_count += 1
        print(f"   [Uloženo] Případ {case_id_gen} zapsán do Supabase.")

    db.close()
    print("==================================================")
    print(f" HOTOVO! ÚSPĚŠNĚ ZPRACOVÁNO NOVÝCH SOUBORŮ: {processed_count} ")
    print("==================================================")

if __name__ == "__main__":
    run_ingestion()
