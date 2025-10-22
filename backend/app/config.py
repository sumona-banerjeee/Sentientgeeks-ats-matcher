import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:sum12345@localhost:5432/sentientgeeks_ats_resume_matcher")
    
    # Ollama Configuration
    USE_OLLAMA: bool = os.getenv("USE_OLLAMA", "true").lower() == "true"
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "https://indoor-boom-stick-determination.trycloudflare.com/")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma3:27b")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "300"))
    PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./data/uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))
    ALLOWED_EXTENSIONS: list = os.getenv("ALLOWED_EXTENSIONS", "pdf,doc,docx").split(",")
    USE_AGENTIC_AI: bool = False
    USE_GROQ: bool = False

settings = Settings()



# Validation on startup
if settings.USE_OLLAMA:
    print("\n" + "="*60)
    print("🤖 OLLAMA INFERENCE MODE ENABLED")
    print("="*60)
    print(f"   Endpoint: {settings.OLLAMA_BASE_URL}")
    print(f"   Model: {settings.OLLAMA_MODEL}")
    print(f"   Timeout: {settings.OLLAMA_TIMEOUT}s")
    print("="*60 + "\n")
else:
    print("⚠️ WARNING: Ollama is disabled in config!")