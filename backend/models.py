from sqlalchemy import Column, Integer, String, Float, Text
from database import Base

class UfoCase(Base):
    __tablename__ = "ufo_cases"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, unique=True, index=True)
    title = Column(String)
    date = Column(String)
    location = Column(String)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(String)
    translation_snippet = Column(Text)
    original_text = Column(Text, nullable=True)
    source_url = Column(String, nullable=True)