# -*- coding: utf-8 -*-
from database import SessionLocal
from models import UfoCase

def fix_database_texts():
    db = SessionLocal()
    cases = db.query(UfoCase).all()
    
    print(f"Opravuji diakritiku u {len(cases)} záznamů v databázi...")
    
    for c in cases:
        # Oprava názvů podle ID nebo klíčových slov
        if "AUTO-DOD_1" in c.case_id:
            c.title = "Senzorový záznam / FLIR telemetrie: DOD_111830007-1920x1080-9000k.mp4"
            c.translation_snippet = "Telemetrická analýza videa: Snímek po snímku rozložená dynamika letu, vysoká úhlová rychlost bez doprovodné zvukové stopy či emisí."
        elif "AUTO-DOW-" in c.case_id:
            c.title = "Odtajněný spis: DOW-UAP-D098_Film-Analysis-of-Unidentified-Objects_1953"
            c.translation_snippet = "Lokální AI analýza spisu: Dokument rozborově potvrzuje anomální charakteristiky, neregistrovanou akceleraci bez viditelných nosných ploch."
        elif "AUTO-FBI-" in c.case_id:
            c.title = "Obrazová analýza: FBI-UAP-D025_Digital-Rendering_Airborne-Triangle_2002.jpg"
            c.translation_snippet = "Optická analýza snímku: Detekován neregistrovaný objekt geometrické konfigurace v optickém spektru."
        elif "MR-75" in c.case_id:
            c.title = "Případ USS Nimitz (Release 01)"
            c.translation_snippet = "Byl detekován anomální objekt bez viditelných nosných ploch. Ztratil tepelnou stopu během teplotního přechodu (thermal crossover)."
        elif "UTAH-1953" in c.case_id:
            c.title = "Analýza filmu - Pozorování Utah"
            c.translation_snippet = "Analýza 16mm filmu: Objekt vykazoval rychlost přes 3780 mph a akceleraci dosahující až 965 g."
        elif "FBI-2026" in c.case_id:
            c.title = "Hlášení FD-302 Více červených světel"
            c.translation_snippet = "Pozorování 6 až 10 červených světel, která se pohybovala v synchronizované formaci a náhle klesla o 1000 stop."

    db.commit()
    db.close()
    print("✅ Diakritika v databázi byla úspěšně opravena!")

if __name__ == "__main__":
    fix_database_texts()