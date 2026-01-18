from sqlalchemy import text
from src.database import DatabaseManager
from loguru import logger

def force_reindex():
    db = DatabaseManager()
    session = db.get_session()
    
    logger.info("--- Starting Force Re-Index ---")
    
    try:
        # 1. Check total products
        count = session.execute(text("SELECT count(*) FROM product_catalog")).scalar()
        logger.info(f"Total Products in Catalog: {count}")
        
        if count == 0:
            logger.error("Catalog is empty! Run ingestion.py first.")
            return

        # 2. Force Update TSVECTOR
        logger.info("Rebuilding Search Vector Index...")
        # We coalesce nulls to empty strings to avoid SQL errors
        sql = text("""
            UPDATE product_catalog 
            SET search_vector = to_tsvector('english', 
                COALESCE(brand_name, '') || ' ' || 
                COALESCE(item_name, '') || ' ' || 
                COALESCE(subcategory_description, '')
            );
        """)
        result = session.execute(sql)
        session.commit()
        logger.success(f"Index Updated. Rows affected: {result.rowcount}")
        
        # 3. Test Verification
        test_term = "iphone"
        verify_sql = text("SELECT count(*) FROM product_catalog WHERE search_vector @@ websearch_to_tsquery('english', :term)")
        found = session.execute(verify_sql, {"term": test_term}).scalar()
        logger.info(f"Verification Search for '{test_term}': Found {found} items.")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Reindex failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    force_reindex()