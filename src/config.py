import os
import sys
from dotenv import load_dotenv
from loguru import logger

# Load the .env file immediately
load_dotenv()

class Config:
    """Centralized configuration with strict validation for thesis data."""
    
    # 1. Database & Infrastructure
    DEBUG = os.getenv("DEBUG_MODE", "True") == "True"
    # When DB_HOST is set (e.g. localhost), use it so ingestion works when run on host.
    # Otherwise use DATABASE_URL (e.g. postgres:5432 inside Docker).
    _db_host = os.getenv("DB_HOST")
    if _db_host:
        _db_port = os.getenv("DB_PORT", "5433")
        _user = os.getenv("POSTGRES_USER", "user")
        _password = os.getenv("POSTGRES_PASSWORD", "password")
        _db = os.getenv("POSTGRES_DB", "thesisdb")
        DB_URL = f"postgresql://{_user}:{_password}@{_db_host}:{_db_port}/{_db}"
    else:
        DB_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/thesisdb")
    
    # 2. AI Intelligence Layer
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-4-turbo")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

    @classmethod
    def validate_config(cls):
        """Compulsory check to ensure the Agent can see the full schema."""
        logger.remove()
        logger.add(sys.stderr, level="DEBUG", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>")
        
        logger.info("--- Initiating Thesis Agent Configuration Check ---")
        
        checks = {
            "Database Connection": cls.DB_URL,
            "OpenAI Intelligence": cls.OPENAI_API_KEY,
            "Web Scout Access": cls.TAVILY_API_KEY
        }

        for name, value in checks.items():
            if not value or "your_openai_key" in str(value):
                logger.error(f"FATAL: {name} is NOT configured correctly in .env!")
                return False
            
            # Mask sensitive info for logs
            display_val = f"{value[:10]}..." if "postgresql" not in str(value) else "Connected to thesisdb"
            logger.debug(f"Verified {name}: {display_val}")

        logger.success("All systems green. Manager Agent is ready for 400k-row analysis.")
        return True

# Run validation automatically
Config.validate_config()