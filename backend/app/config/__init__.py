import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:sum12345@localhost:5432/sentientgeeks_ats_resume_matcher")
    
    # Primary Ollama Configuration
    USE_OLLAMA: bool = os.getenv("USE_OLLAMA", "false").lower() == "true"
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma3:27b")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "300"))
    
    # Fallback Perplexity Configuration
    PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")
    USE_PERPLEXITY_FALLBACK: bool = True 
    
    
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    

    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./data/uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))
    ALLOWED_EXTENSIONS: list = os.getenv("ALLOWED_EXTENSIONS", "pdf,doc,docx").split(",")
    
    
    USE_AGENTIC_AI: bool = False
    USE_GROQ: bool = False



    USE_PERPLEXITY: bool = os.getenv("USE_PERPLEXITY", "true").lower() == "true"
    PERPLEXITY_MODEL: str = os.getenv("PERPLEXITY_MODEL", "sonar-pro")

settings = Settings()


if settings.USE_OLLAMA:
    if settings.OLLAMA_BASE_URL:
        print("\n" + " "*60)
        print("PRIMARY: OLLAMA INFERENCE MODE")
        print(" "*60)
        print(f"   Endpoint: {settings.OLLAMA_BASE_URL}")
        print(f"   Model: {settings.OLLAMA_MODEL}")
        print(f"   Timeout: {settings.OLLAMA_TIMEOUT}s")
        print(f"   Fallback: Perplexity API ({settings.PERPLEXITY_API_KEY[:20]}...)")
        print("="*60 + "\n")
    else:
        print("WARNING: Ollama enabled but no URL provided. Falling back to Perplexity.")
        settings.USE_OLLAMA = False

if not settings.USE_OLLAMA:
    if settings.PERPLEXITY_API_KEY:
        print("\n" + " "*60)
        print("PRIMARY: PERPLEXITY API MODE")
        print(" "*60)
        print(f"   API Key: {settings.PERPLEXITY_API_KEY[:20]}...")
        print(f"   Model: sonar-pro")
        print(" "*60 + "\n")
    else:
        print("ERROR: No LLM service configured!")
        print("   Please set either:")
        print("   OLLAMA_BASE_URL (for Ollama)")
        print("   PERPLEXITY_API_KEY (for Perplexity)")