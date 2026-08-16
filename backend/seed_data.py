from database import SessionLocal
from models import UfoCase

def seed_database():
    db = SessionLocal()
    
    # Zkontrolujeme, zda už v databázi něco není
    existing = db.query(UfoCase).first()
    if existing:
        print("ℹ️ Databáze již obsahuje záznamy. Vkládání je přeskočeno.")
        db.close()
        return

    print("📥 Vkládám úvodní badatelské UAP případy do Supabase...")

    cases = [
        UfoCase(
            case_id="MR-75",
            title="Případ USS Nimitz (Release 01)",
            date="2004-11-14",
            location="Tichý oceán",
            latitude=32.5,
            longitude=-120.5,
            status="Unresolved",
            translation_snippet="Byl detekován anomální objekt bez viditelných nosných ploch. Ztratil tepelnou stopu během teplotního přechodu (thermal crossover).",
            original_text="Anomalous object detected with no visible flight control surfaces. Lost thermal signature during thermal crossover.",
            source_url="https://www.war.gov/UFO/"
        ),
        UfoCase(
            case_id="UTAH-1953",
            title="Film Analysis - Utah Sighting",
            date="1952-07-02",
            location="Utah, USA",
            latitude=40.7608,
            longitude=-111.8910,
            status="Unresolved",
            translation_snippet="Analýza 16mm filmu: Objekt vykazoval rychlost přes 3780 mph a akceleraci dosahující až 965 g.",
            original_text="Interpretation of Movies of Unidentified Objects; velocity computed to be 3780 mph for a shift of 1 mm per frame.",
            source_url="https://www.war.gov/UFO/"
        ),
        UfoCase(
            case_id="FBI-2026",
            title="FD-302 Multiple Red Lights",
            date="2026-02-10",
            location="Nevada Range, USA",
            latitude=37.2350,
            longitude=-115.8111,
            status="Unresolved",
            translation_snippet="Pozorování 6 až 10 červených světel, která se pohybovala v synchronizované formaci a náhle klesla o 1000 stop.",
            original_text="Multiple more (approximately 6 to 10) lights appeared directly over their position, appeared to sync up and traveled east/southeast.",
            source_url="https://www.war.gov/UFO/"
        )
    ]

    for c in cases:
        db.add(c)
    
    db.commit()
    db.close()
    print("✅ Úvodní případy byly úspěšně uloženy do cloudové databáze!")

if __name__ == "__main__":
    seed_database()