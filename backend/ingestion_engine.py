# -*- coding: utf-8 -*-
import os
import re
import fitz  # PyMuPDF
from database import SessionLocal
from models import UfoCase
from ai_engine import translate_ufo_text

def process_incoming_files():
    # Nastavení absolutní cesty dle tvé struktury
    incoming_dir = os.path.join(os.path.dirname(__file__), "incoming_data")
    
    if not os.path.exists(incoming_dir):
        print(f"Složka '{incoming_dir}' neexistuje!")
        return

    files = os.listdir(incoming_dir)
    db = SessionLocal()
    
    print(f"🚀 Zahajuji lokální analýzu {len(files)} souborů...")

    for file_name in files:
        file_path = os.path.join(incoming_dir, file_name)
        if os.path.isdir(file_path):
            continue

        print(f"\nZpracovávám: {file_name}")
        ext = file_name.split('.')[-1].lower()
        
        # Ošetření ID, aby neobsahovalo zakázané znaky a bylo unikátní
        clean_name = file_name.replace(' ', '-').replace('_', '-')
        case_id_gen = f"UAP-{clean_name[:40].upper()}"
        
        # Kontrola, zda už případ není v DB (šetří API volání)
        existing = db.query(UfoCase).filter(UfoCase.case_id == case_id_gen).first()
        if existing:
            print(f"⏭️ Případ {case_id_gen} již existuje. Přeskakuji.")
            continue

        original_text = f"Zdrojový soubor: {file_name}"
        snippet = "Čeká na zpracování..."
        title = f"Odtajněný spis: {file_name}"
        detected_date = "2026-01-01"
        lat, lon = 37.2350, -115.8111 # Default Area 51

        # ANALÝZA PDF
        if ext == 'pdf':
            try:
                doc = fitz.open(file_path)
                extracted_pages = [page.get_text() for page in doc[:5]] # Projdeme max prvních 5 stran pro úsporu
                full_pdf_text = "\n".join(extracted_pages).strip()
                
                if full_pdf_text:
                    original_text = full_pdf_text[:3000]
                    # Volání OpenAI přes náš upravený ai_engine
                    print("   - Volám OpenAI pro analýzu a překlad...")
                    snippet = translate_ufo_text(original_text)
                    
                    date_match = re.search(r'\b(19\d{2}|20\d{2})\b', full_pdf_text)
                    if date_match:
                        detected_date = f"{date_match.group(1)}-01-01"
                else:
                    original_text = "Skenovaný obrazový dokument. Vyžaduje hluboké OCR."
                    snippet = "Tento PDF dokument obsahuje převážně skenované obrázky bez textové vrstvy."
            except Exception as e:
                snippet = f"Chyba parsování PDF: {e}"

        # ANALÝZA OBRÁZKŮ (.jpg, .png)
        elif ext in ['jpg', 'jpeg', 'png']:
            title = f"Obrazový důkaz: {file_name}"
            snippet = "Optická analýza vizuálního záznamu odtajněného z war.gov/UFO."
            
        # ANALÝZA VIDEA (.mp4)
        elif ext in ['mp4']:
            title = f"Senzorový záznam HUD/FLIR: {file_name}"
            snippet = "Videometrická data připravená k budoucí pohybové analýze v modulu OpenCV."

        else:
            continue

        # Uložení do Supabase
        new_case = UfoCase(
            case_id=case_id_gen,
            title=title,
            date=detected_date,
            location="USA / war.gov/UFO",
            latitude=lat,
            longitude=lon,
            status="Unresolved",
            translation_snippet=snippet,
            original_text=original_text,
            source_url="https://www.war.gov/UFO/"
        )

        try:
            db.add(new_case)
            db.commit()
            print(f"✅ Uloženo do databáze: {case_id_gen}")
        except Exception as e:
            db.rollback()
            print(f"❌ Chyba ukládání do DB: {e}")

    db.close()
    print("\n🎉 Všechna lokální data byla prozkoumána a uložena do Supabase!")

if __name__ == "__main__":
    process_incoming_files()
