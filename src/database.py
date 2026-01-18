import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, BigInteger, Index
from sqlalchemy.orm import declarative_base, sessionmaker, Session, mapped_column
from sqlalchemy.sql import text
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector
from loguru import logger
from src.config import Config

Base = declarative_base()

class ProductCatalog(Base):
    __tablename__ = 'product_catalog'
    
    asin = Column(String(50), primary_key=True)
    item_name = Column(Text, nullable=False)
    brand_name = Column(String(100))
    manufacturer_name = Column(String(100))
    subcategory_description = Column(String(100))
    
    # 1. SEMANTIC BRAIN: Vectors
    embedding = mapped_column(Vector(1536))
    
    # 2. KEYWORD BRAIN: Full Text Search
    search_vector = Column(TSVECTOR)

    # Indexes
    __table_args__ = (
        Index('idx_product_embedding', 'embedding', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'}),
        Index('idx_product_search', 'search_vector', postgresql_using='gin'),
    )

class ShippedRaw(Base):
    __tablename__ = 'shipped_raw'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ncrc_su_pk = Column(String(100))
    asin = Column(String(50), index=True)
    
    # --- ADDED: Critical Categorization Columns ---
    item_name = Column(Text)                   # <--- Added
    brand_name = Column(String(100), index=True)      # <--- Added
    manufacturer_name = Column(String(100))           # <--- Added
    # ----------------------------------------------

    child_vendor_code = Column(String(50))
    gl_product_group = Column(Integer)
    subcategory_code = Column(String(50))
    marketplace_id = Column(Integer)
    fulfillment_channel = Column(String(20))
    
    year = Column(Integer)
    month = Column(Integer)
    quarter = Column(Integer)
    week = Column(Integer)
    
    mapped_year = Column(Integer, index=True)
    
    shipped_units = Column(Integer)
    shipped_cogs = Column(Float)
    product_gms = Column(Float)
    asp_bucket = Column(String(50))
    is_b2b = Column(String(10))

class ConcessionRaw(Base):
    __tablename__ = 'concession_raw'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ncrc_cu_pk = Column(String(100))
    asin = Column(String(50), index=True)

    # --- ADDED: Critical Categorization Columns ---
    item_name = Column(Text)                   # <--- Added
    brand_name = Column(String(100), index=True)      # <--- Added
    manufacturer_name = Column(String(100))           # <--- Added
    marketplace_id = Column(Integer)                  # <--- Added
    product_type = Column(String(50))                 # <--- Added
    # ----------------------------------------------

    year = Column(Integer)
    month = Column(Integer)
    quarter = Column(Integer)
    week = Column(Integer)
    
    # --- ADDED: The Golden Linking Columns ---
    mapped_year = Column(Integer, index=True)
    mapped_month = Column(Integer, index=True)
    mapped_week = Column(Integer)
    mapped_quarter = Column(Integer)
    # -----------------------------------------

    conceded_units = Column(Integer)
    gcv = Column(Float)
    returned_cogs = Column(Float)
    ncrc = Column(Float)
    return_window = Column(String(50))
    recovery_channel = Column(String(50))
    defect_category = Column(String(255))
    root_cause = Column(String(255))
    is_outside_of_return_window = Column(String(10))

    # Alert Flags
    is_hrr_asin = Column(String(10))
    is_andon_cord = Column(String(10))

class DatabaseManager:
    def __init__(self):
        try:
            self.engine = create_engine(Config.DB_URL)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        except Exception as e:
            logger.error(f"DB Init Failed: {e}")
            sys.exit(1)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def init_db(self):
        try:
            with self.engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
            Base.metadata.create_all(bind=self.engine)
            logger.success("Schema Updated: Added Full-Text Search (TSVECTOR).")
        except Exception as e:
            logger.error(f"Schema creation failed: {e}")

if __name__ == "__main__":
    db = DatabaseManager()
    db.init_db()