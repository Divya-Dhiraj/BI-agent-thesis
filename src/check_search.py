from sqlalchemy import text
from src.database import DatabaseManager
from loguru import logger

def check_search_results(keyword="iphone 13"):
    db = DatabaseManager()
    session = db.get_session()
    
    logger.info(f"--- Inspecting Search Hits for '{keyword}' ---")
    
    try:
        # We query the exact same index the Agent uses
        sql = text("""
            SELECT asin, item_name 
            FROM product_catalog 
            WHERE search_vector @@ websearch_to_tsquery('english', :term)
            LIMIT 20;
        """)
        
        results = session.execute(sql, {"term": keyword}).fetchall()
        
        if not results:
            logger.warning("No matches found.")
        else:
            logger.success(f"Displaying top {len(results)} matches:")
            print("\n" + "="*80)
            print(f"{'ASIN':<15} | {'PRODUCT NAME'}")
            print("="*80)
            for asin, name in results:
                # Truncate name for cleaner display
                clean_name = name[:60] + "..." if len(name) > 60 else name
                print(f"{asin:<15} | {clean_name}")
            print("="*80 + "\n")
            
    except Exception as e:
        logger.error(f"Search check failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # You can change this string to test other queries like "samsung" or "headphones"
    check_search_results("iphone 13")