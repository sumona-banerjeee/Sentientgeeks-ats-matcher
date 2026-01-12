import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:sum12345@localhost:5432/sentientgeeks_ats_resume_matcher")
    
    # llama.cpp Server Configuration (OpenAI-compatible)
    USE_LLAMACPP: bool = os.getenv("USE_LLAMACPP", "false").lower() == "true"
    LLAMACPP_BASE_URL: str = os.getenv("LLAMACPP_BASE_URL", "")
    LLAMACPP_API_KEY: str = os.getenv("LLAMACPP_API_KEY", "sk-no-key-required")
    LLAMACPP_MODEL: str = os.getenv("LLAMACPP_MODEL", "")
    LLAMACPP_TIMEOUT: int = int(os.getenv("LLAMACPP_TIMEOUT", "120"))
    
    # Primary Ollama Configuration
    USE_OLLAMA: bool = os.getenv("USE_OLLAMA", "false").lower() == "true"
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "")
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

    USE_PERPLEXITY: bool = os.getenv("USE_PERPLEXITY", "false").lower() == "true"
    PERPLEXITY_MODEL: str = os.getenv("PERPLEXITY_MODEL", "sonar-pro")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "")

settings = Settings()

# Startup configuration display
if settings.USE_LLAMACPP:
    if settings.LLAMACPP_BASE_URL:
        print("\n" + "="*70)
        print("🚀 PRIMARY: LLAMA.CPP SERVER (OpenAI-Compatible)")
        print("="*70)
        print(f"   Endpoint: {settings.LLAMACPP_BASE_URL}")
        print(f"   Model: {settings.LLAMACPP_MODEL}")
        print(f"   Timeout: {settings.LLAMACPP_TIMEOUT}s")
        print(f"   Fallback: Perplexity API")
        print("="*70 + "\n")
    else:
        print("⚠️ WARNING: USE_LLAMACPP enabled but no LLAMACPP_BASE_URL provided")
        settings.USE_LLAMACPP = False

elif settings.USE_OLLAMA:
    if settings.OLLAMA_BASE_URL:
        print("\n" + "="*70)
        print("🤖 PRIMARY: OLLAMA INFERENCE MODE")
        print("="*70)
        print(f"   Endpoint: {settings.OLLAMA_BASE_URL}")
        print(f"   Model: {settings.OLLAMA_MODEL}")
        print(f"   Timeout: {settings.OLLAMA_TIMEOUT}s")
        print(f"   Fallback: Perplexity API")
        print("="*70 + "\n")
    else:
        print("⚠️ WARNING: Ollama enabled but no URL provided. Falling back to Perplexity.")
        settings.USE_OLLAMA = False

if not settings.USE_LLAMACPP and not settings.USE_OLLAMA:
    if settings.PERPLEXITY_API_KEY:
        print("\n" + "="*70)
        print("🔑 PRIMARY: PERPLEXITY API MODE")
        print("="*70)
        print(f"   API Key: {settings.PERPLEXITY_API_KEY[:20]}...")
        print(f"   Model: {settings.PERPLEXITY_MODEL}")
        print("="*70 + "\n")
    else:
        print("❌ ERROR: No LLM service configured!")
        print("   Please set either:")
        print("   - LLAMACPP_BASE_URL (for llama.cpp server)")
        print("   - OLLAMA_BASE_URL (for Ollama)")
        print("   - PERPLEXITY_API_KEY (for Perplexity)")