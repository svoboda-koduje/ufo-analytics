# -*- coding: utf-8 -*-
"""
SQLAlchemy databázový model pro tabulku ufo_cases v Supabase.
"""

from sqlalchemy import Column, BigInteger, String, Text, Float, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class UfoCase(Base):
    __tablename__ = "ufo_cases"

    id = Column(BigInteger, primary_key=True, index=True)
    case_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    asset_file_name = Column(Text, nullable=True)
    file_type = Column(String(50), nullable=True)
    agency = Column(String(150), nullable=True)
    release_tag = Column(String(100), nullable=True)
    incident_date = Column(String(100), nullable=True)
    incident_year = Column(Integer, nullable=True)
    location = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(String(50), default="Unresolved")
    original_text = Column(Text, nullable=True)
    czech_translation = Column(Text, nullable=True)
    search_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Dynamické aliasy pro zpětnou kompatibilitu s endpointy API
    @property
    def date(self):
        return self.incident_date

    @property
    def translation_snippet(self):
        return self.czech_translation

    @property
    def source_url(self):
        return self.search_url
