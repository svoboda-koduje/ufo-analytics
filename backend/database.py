import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Načte tajné proměnné ze souboru .env (např. heslo k Supabase)
load_dotenv()

# Vezme adresu databáze z proměnné prostředí
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://ufo_admin:secretpassword@localhost:5432/ufo_cases"
)

# Fix pro cloudové služby: SQLAlchemy vyžaduje postgresql://
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Založení spojení s databází
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Funkce pro získání databáze pro API endpointy
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()