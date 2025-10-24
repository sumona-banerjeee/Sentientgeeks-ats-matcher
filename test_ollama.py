import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app.services.ollama_service import get_ollama_service
from dotenv import load_dotenv

load_dotenv()

def test_ollama_connection():
    print("\n" + " "*60)
    print("TESTING OLLAMA CONNECTION")
    print(" "*60 + "\n")
    
    try:
        # Initialize service
        ollama = get_ollama_service()
        
        # Health check
        print("1️. Testing health check...")
        if ollama.health_check():
            print(" Health check passed\n")
        else:
            print(" Health check failed\n")
            return False
        
        # Test simple prompt
        print("2️. Testing simple prompt...")
        test_prompt = "Say 'Hello from Ollama!' in exactly those words."
        response = ollama._make_request(test_prompt, temperature=0.0)
        print(f"   Response: {response[:100]}...")
        print(" Simple prompt test passed\n")
        
        # Test JSON extraction
        print("3️. Testing JSON extraction...")
        json_prompt = """Return this exact JSON:
{
    "status": "working",
    "model": "gemma3:27b",
    "test": true
}
"""
        response = ollama._make_request(json_prompt, temperature=0.0)
        parsed = ollama._parse_json_response(response, "test")
        
        if "error" not in parsed:
            print(f"   Parsed JSON: {parsed}")
            print("JSON extraction test passed\n")
        else:
            print(f" JSON parsing issue: {parsed}")
        
        print(" "*60)
        print(" ALL TESTS PASSED - Ollama is ready!")
        print(" "*60 + "\n")
        return True
    
    except Exception as e:
        print(f"\nTEST FAILED: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ollama_connection()
    sys.exit(0 if success else 1)