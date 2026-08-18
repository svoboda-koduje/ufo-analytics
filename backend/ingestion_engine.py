# -*- coding: utf-8 -*-
import os
import re
import fitz  # PyMuPDF
from database import SessionLocal
from models import UfoCase
from ai_engine import analyze_and_translate_ufo_text

def process_incoming_files():
    incoming_dir = os.path.join(os.path.dirname(__file__), "incoming_data")
    
    if not os.path.exists(incoming_dir):
        print(f"Složka '{incoming_dir}' neexistuje!")
        return

    files = os.listdir(incoming_dir)
    db = SessionLocal()
    
    print(f"🚀 Zahajuji geolokační a textovou analýzu {len(files)} souborů...")

    for file_name in files:
        file_path = os.path.join(incoming_dir, file_name)
        if os.path.isdir(file_path):
            continue

        print(f"\nZpracovávám: {file_name}")
        ext = file_name.split('.')[-1].lower()
        
        clean_name = file_name.replace(' ', '-').replace('_', '-')
        case_id_gen = f"UAP-{clean_name[:20].upper()}"
        
        existing = db.query(UfoCase).filter(UfoCase.case_id == case_id_gen).first()
        if existing:
            print(f"⏭️ Případ {case_id_gen} již existuje. Přeskakuji.")
            continue

        original_text = f"Zdrojový soubor: {file_name}"
        snippet = "Čeká na zpracování..."
        title = f"Odtajněný spis: {file_name}"
        detected_date = "2026-01-01"
        
        # Výchozí souřadnice, pokud by vše ostatní selhalo
        lat, lon = 37.2350, -115.8111

        # ANALÝZA PDF
        if ext == 'pdf':
            try:
                doc = fitz.open(file_path)
                extracted_pages = [page.get_text() for page in doc[:5]]
                full_pdf_text = "\n".join(extracted_pages).strip()
                
                if full_pdf_text:
                    original_text = full_pdf_text[:3000]
                    print("   - Volám OpenAI pro AI geolokaci a překlad...")
                    
                    # VOLÁNÍ NOVÉ AI FUNKCE
                    ai_result = analyze_and_translate_ufo_text(original_text, file_name)
                    
                    snippet = ai_result.get("translation_snippet", "Chyba překladu")
                    lat = ai_result.get("latitude", lat)
                    lon = ai_result.get("longitude", lon)
                    
                    date_match = re.search(r'\b(19\d{2}|20\d{2})\b', full_pdf_text)
                    if date_match:
                        detected_date = f"{date_match.group(1)}-01-01"
                else:
                    original_text = "Skenovaný obrazový dokument. Vyžaduje hluboké OCR."
                    # Zkusíme geolokaci alespoň z názvu souboru
                    ai_result = analyze_and_translate_ufo_text("Dokument bez textové vrstvy.", file_name)
                    snippet = ai_result.get("translation_snippet", "Dokument obsahuje pouze skenované obrázky.")
                    lat = ai_result.get("latitude", lat)
                    lon = ai_result.get("longitude", lon)
            except Exception as e:
                snippet = f"Chyba parsování PDF: {e}"

        # ANALÝZA OBRÁZKŮ A VIDEÍ (.jpg, .png, .mp4)
        elif ext in ['jpg', 'jpeg', 'png', 'mp4']:
            if ext == 'mp4':
                title = f"Senzorový záznam HUD/FLIR: {file_name}"
            else:
                title = f"Obrazový důkaz: {file_name}"
            
            print("   - Volám OpenAI pro pokus o geolokaci metadat z názvu...")
            # Obrázky a videa nemají text, posíláme AI jen název souboru k vyhodnocení
            ai_result = analyze_and_translate_ufo_text("Obrazový/video záznam - vizuální analýza.", file_name)
            snippet = ai_result.get("translation_snippet", "Optická analýza vizuálního záznamu.")
            lat = ai_result.get("latitude", lat)
            lon = ai_result.get("longitude", lon)

        else:
            continue

        # Uložení do Supabase se specifickými souřadnicemi pro každý případ!
        new_case = UfoCase(
            case_id=case_id_gen,
            title=title,
            date=detected_date,
            location="Dle AI analýzy",
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
            print(f"✅ Uloženo: {case_id_gen} [Lokace: {lat}, {lon}]")
        except Exception as e:
            db.rollback()
            print(f"❌ Chyba ukládání do DB: {e}")

    db.close()
    print("\n🎉 Geolokační analýza a vkládání do databáze bylo dokončeno!")

if __name__ == "__main__":
    process_incoming_files()
