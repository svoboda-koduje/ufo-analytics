from sqlalchemy import text
from database import engine, Base
import models

def init_remote_db():
    print("🔌 Připojuji se k Supabase databázi...")
    
    try:
        # 1. Aktivace mapového rozšíření PostGIS
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
            print("🌍 Mapové funkce (PostGIS) byly úspěšně aktivovány.")

        # 2. Vyčištění staré struktury a vytvoření nové tabulky se všemi sloupci (včetně case_id)
        Base.metadata.drop_all(bind=engine)
        print("🗑️ Stará struktura tabulek byla vyčištěna.")
        
        Base.metadata.create_all(bind=engine)
        print("✅ Tabulka pro UAP/UFO případy byla úspěšně vytvořena se všemi sloupci!")
        print("🎉 Databáze je kompletně připravená.")

    except Exception as e:
        print(f"❌ Nastala chyba při připojení: {e}")

if __name__ == "__main__":
    init_remote_db()