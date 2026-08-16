import os
import hashlib
from sqlalchemy.orm import Session
from database import SessionLocal
import models

def calculate_sha256(file_path: str) -> str:
    """
    Vygeneruje SHA-256 kontrolní součet souboru pro účely deduplikace.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def process_incoming_release(release_name: str, source_url: str):
    """
    Download Manager & Deduplicator: Stáhne archiv, spočítá SHA-256 a ověří unikátnost.
    """
    print(f"📥 [Ingesční modul] Zahajuji stahování balíčku {release_name} z {source_url}...")
    
    # Simulace uložení surového souboru do lokálního úložiště (v produkci AWS S3 / MinIO)[cite: 2]
    storage_dir = "./cloud_storage_raw"
    os.makedirs(storage_dir, exist_ok=True)
    file_path = os.path.join(storage_dir, f"{release_name}.zip")
    
    # Vytvoření testovacího binárního obsahu pro ukázku
    with open(file_path, "wb") as f:
        f.write(f"Raw data package content for {release_name} from war.gov/UFO".encode('utf-8'))
        
    # Generování SHA-256 kontrolního součtu[cite: 2]
    file_hash = calculate_sha256(file_path)
    print(f"🔐 [Deduplikace] Vygenerován SHA-256 pro {release_name}: {file_hash}")
    
    # Kontrola duplicit v PostGIS databázi
    db: Session = SessionLocal()
    try:
        # Hledáme, zda již stejný hash v metadatech neexistuje
        existing_case = db.query(models.UfoCase).filter(models.UfoCase.metadata_json.ilike(f"%{file_hash}%")).first()
        
        if existing_case:
            print(f"⚠️ [Deduplikace] Balíček {release_name} již byl dříve zpracován (shoda SHA-256). Přeskakuji.")
            return {"status": "skipped", "reason": "duplicate", "sha256": file_hash}
            
        print(f"✅ [Object Storage] Surový balíček {release_name} úspěšně uložen do úložiště a ověřen.")
        return {"status": "success", "sha256": file_hash}
        
    finally:
        db.close()
