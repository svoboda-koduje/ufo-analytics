import os
import json
import base64
import time
from pathlib import Path
import pymupdf  # PyMuPDF
import cv2
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not OPENAI_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ CHYBA: V souboru .env chybí klíče pro OpenAI nebo Supabase!")
    exit(1)

openai_client = OpenAI(api_key=OPENAI_API_KEY, timeout=35.0, max_retries=2)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

INCOMING_DIR = Path(__file__).parent / "incoming_data"

def pdf_page_to_base64(page):
    """Převede stránku skenovaného PDF na optimalizovaný JPEG pro GPT-4o Vision."""
    try:
        pix = page.get_pixmap(dpi=120)
        img_bytes = pix.tobytes("jpeg")
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        print(f"⚠️ Chyba konverze stránky: {e}")
        return None

def extract_file_content(file_path):
    ext = file_path.suffix.lower()
    raw_text = ""
    images_b64 = []
    file_type = "PDF"

    if ext == '.pdf':
        file_type = "PDF"
        try:
            doc = pymupdf.open(file_path)
            for page_num in range(len(doc)):
                t = doc[page_num].get_text()
                if t:
                    raw_text += f"\n--- Strana {page_num + 1} ---\n" + t
                if len(raw_text) > 4000:
                    break
            
            # Pokud je PDF naskenovaný obraz bez textu, převedeme 1. stranu na obrázek
            if len(raw_text.strip()) < 80 and len(doc) > 0:
                img_b64 = pdf_page_to_base64(doc[0])
                if img_b64:
                    images_b64.append(img_b64)
        except Exception as e:
            print(f"⚠️ Chyba při čtení PDF: {e}")

    elif ext in ('.jpg', '.jpeg', '.png'):
        file_type = "IMG"
        raw_text = f"Obrazový záznam / digitální rendering UAP: {file_path.name}"
        try:
            with open(file_path, "rb") as f:
                images_b64.append(base64.b64encode(f.read()).decode('utf-8'))
        except Exception as e:
            print(f"⚠️ Chyba při čtení obrázku: {e}")

    elif ext == '.mp4':
        file_type = "VID"
        raw_text = f"Videozáznam senzorového systému / telemetrie UAP: {file_path.name}"
        try:
            cap = cv2.VideoCapture(str(file_path))
            if cap.isOpened():
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(total_frames * 0.2))
                ret, frame = cap.read()
                if ret:
                    frame_resized = cv2.resize(frame, (800, int(800 * frame.shape[0] / frame.shape[1])))
                    _, buffer = cv2.imencode('.jpg', frame_resized, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                    images_b64.append(base64.b64encode(buffer.tobytes()).decode('utf-8'))
                cap.release()
        except Exception as e:
            print(f"⚠️ Chyba při čtení videa: {e}")

    return raw_text.strip(), images_b64, file_type

def analyze_with_openai(filename, raw_text, images_b64):
    system_prompt = (
        "Jsi hlavní vojenský a letecký analytik UAP/UFO odtajněných spisů Ministerstva války USA a AARO. "
        "Tvým úkolem je extrahovat skutečná fakta z dokumentu a poskytnout přesný odborný český překlad. "
        "Vracíš výhradně validní JSON objekt."
    )

    prompt_text = f"""Analyzuj odtajněný spis: {filename}
Obsah textové vrstvy spisu:
---
{raw_text[:3500] if raw_text else "Textová vrstva není přítomna, čti přiložený obrazový materiál."}
---

Vrať JSON objekt s těmito klíči:
- "agency": vládní instituce (např. "DEPARTMENT OF WAR", "CIA", "FBI", "USAF", "NASA")
- "incident_date": datum incidentu (např. "1950, 1952" nebo "2001-10-30")
- "incident_year": rok incidentu jako celé číslo (např. 1950)
- "location": přesná lokalita nebo oblast (např. "MONTANA, UTAH", "KAZACHSTÁN")
- "latitude": zeměpisná šířka (float, např. 46.8797, výchozí pro USA 38.8951)
- "longitude": zeměpisná délka (float, např. -110.3626, výchozí -77.0364)
- "status": "Unresolved" (nevysvětleno) nebo "Resolved" (identifikováno)
- "original_text": SKUTEČNÝ, PODROBNÝ PŘEPIS NEBO STRUKTUROVANÝ EXTRAKT Z DOKUMENTU V ANGLIČTINĚ (žádné obecné zástupné věty, přepiš konkrétní fakta a telemetrii z dokumentu).
- "czech_translation": ODBORNÝ ČESKÝ PŘEKLAD A ANALÝZA se zachováním vojenské a letecké terminologie (Range Fouler, Thermal Crossover, Azimuth, FLIR, HUD, apod.).
"""

    user_content = [{"type": "text", "text": prompt_text}]
    for img in images_b64[:1]:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img}", "detail": "low"}
        })

    for attempt in range(4):
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            return json.loads(response.choices[0].message.content.strip())
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate limit" in err_str.lower():
                wait_sec = (attempt + 1) * 3
                print(f"   ⚠️ Rate limit (429). Čekám {wait_sec}s...")
                time.sleep(wait_sec)
            else:
                print(f"   ❌ Chyba OpenAI API: {e}")
                return None
    return None

def run_test_20():
    if not INCOMING_DIR.exists():
        print(f"❌ Adresář {INCOMING_DIR} neexistuje!")
        return

    # Načtení existujících řádků ze Supabase pro bezpečný update podle ID
    print("📡 Načítám mapu existujících záznamů ze Supabase...")
    try:
        db_cases = supabase.table("ufo_cases").select("id, title, asset_file_name, case_id").execute().data
    except Exception as e:
        print(f"❌ Nelze se spojit se Supabase: {e}")
        return

    supported_exts = ('.pdf', '.jpg', '.jpeg', '.png', '.mp4')
    all_disk_files = [f for f in sorted(INCOMING_DIR.iterdir()) if f.suffix.lower() in supported_exts]
    test_files = all_disk_files[:20]

    print(f"\n🚀 SPUŠTĚNÍ TESTU PRO PRVNÍCH {len(test_files)} SOUBORŮ\n" + "=" * 60)

    for idx, file_path in enumerate(test_files, 1):
        filename = file_path.name
        print(f"\n[{idx}/20] 📄 Soubor: {filename}")

        # Nalezení existujícího řádku v DB
        matched_row = None
        for row in db_cases:
            if filename in str(row.get("title", "")) or filename in str(row.get("asset_file_name", "")) or filename in str(row.get("case_id", "")):
                matched_row = row
                break

        raw_text, images_b64, file_type = extract_file_content(file_path)
        print(f"   ↳ Extrahováno znaků: {len(raw_text)} | Přiložených snímků: {len(images_b64)} | Typ: {file_type}")

        analysis = analyze_with_openai(filename, raw_text, images_b64)
        if not analysis:
            print(f"   ⚠️ Analýza OpenAI selhala, přeskakuji.")
            continue

        print(f"   ✅ OpenAI analýza dokončena:")
        print(f"      • Datum: {analysis.get('incident_date')} | Lokace: {analysis.get('location')} | Status: {analysis.get('status')}")
        print(f"      • Originál (úryvek): {str(analysis.get('original_text', ''))[:120]}...")
        print(f"      • Překlad (úryvek):  {str(analysis.get('czech_translation', ''))[:120]}...")

        # Příprava dat pro zápis do Supabase
        update_data = {
            "agency": str(analysis.get("agency", "DEPARTMENT OF WAR")),
            "incident_date": str(analysis.get("incident_date", "N/A")),
            "incident_year": int(analysis.get("incident_year", 2026)) if str(analysis.get("incident_year", "")).isdigit() else 2026,
            "location": str(analysis.get("location", "Neznámá lokace")),
            "latitude": float(analysis.get("latitude", 38.8951)) if analysis.get("latitude") else 38.8951,
            "longitude": float(analysis.get("longitude", -77.0364)) if analysis.get("longitude") else -77.0364,
            "status": str(analysis.get("status", "Unresolved")),
            "original_text": str(analysis.get("original_text", raw_text[:2000])),
            "czech_translation": str(analysis.get("czech_translation", "Překlad se zpracovává."))
        }

        try:
            if matched_row:
                supabase.table("ufo_cases").update(update_data).eq("id", matched_row["id"]).execute()
                print(f"   💾 Aktualizován záznam v Supabase (ID {matched_row['id']}): {matched_row.get('case_id')}")
            else:
                update_data["case_id"] = f"UAP-{idx:03d}-{filename.split('.')[0][:30]}"
                update_data["title"] = f"Odtajněný spis: {filename}"
                update_data["asset_file_name"] = filename
                update_data["file_type"] = file_type
                supabase.table("ufo_cases").insert(update_data).execute()
                print(f"   💾 Vložen nový záznam do Supabase: {filename}")
        except Exception as db_err:
            print(f"   ❌ Chyba zápisu do Supabase: {db_err}")

        time.sleep(1.0)

    print("\n" + "=" * 60 + "\n🎉 TESTOVACÍ DÁVKA 20 SOUBORŮ DOKONČENA!")

if __name__ == "__main__":
    run_test_20()