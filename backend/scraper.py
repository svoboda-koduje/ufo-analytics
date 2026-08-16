import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from ai_engine import translate_ufo_text

def check_for_new_data():
    print("🔍 Spouštím průzkum a ingesci nových dat z war.gov/UFO...")
    
    db: Session = SessionLocal()
    try:
        # Generujeme unikátní název s časovým razítkem, aby nedocházelo k přeskakování duplicit
        now_str = datetime.now().strftime("%H:%M:%S")
        unique_title = f"Případ anomálie (Live Test {now_str})"
        
        simulated_war_gov_cases = [
            {
                "case_id": f"Live-{now_str}",
                "title": unique_title,
                "date": datetime.now(),
                "status": "Unresolved",
                "latitude": 32.3 + (datetime.now().minute % 10),
                "longitude": -64.8 - (datetime.now().second % 10),
                "english_description": "High-altitude object performing instantaneous vector changes without aerodynamic surfaces."
            }
        ]
        
        new_records_count = 0
        for item in simulated_war_gov_cases:
            # Přeskočíme kontrolu duplicit, abychom viděli, že se data hned propíšou do frontendu
            translated_text = translate_ufo_text(item["english_description"])
            
            point = Point(item["longitude"], item["latitude"])
            new_case = models.UfoCase(
                title=item["title"],
                date=item["date"],
                status=item["status"],
                location=from_shape(point, srid=4326),
                translation=translated_text,
                metadata_json='{"source": "war.gov/UFO", "type": "Live-Test"}'
            )
            db.add(new_case)
            new_records_count += 1
        
        db.commit()
        print(f"✅ Ingesce a AI překlad dokončeny. Přidáno nových případů: {new_records_count}")
    
    except Exception as e:
        db.rollback()
        print(f"❌ CHYBA při ingesci a překladu: {str(e)}")
    finally:
        db.close()
