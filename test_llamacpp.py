from backend.app.services.llamacpp_service import get_llamacpp_service

def test_llamacpp():
    print("Testing llama.cpp service...")
    
    try:
        service = get_llamacpp_service()
        
        # Test health check
        if service.health_check():
            print("llama.cpp server is healthy")
        else:
            print("llama.cpp server health check failed")
            return
        
        # Test simple request
        test_prompt = "What is 2+2?"
        response = service._make_request(test_prompt, temperature=0.1)
        print(f"\nTest Response: {response}")
        
        print("\nllama.cpp service is working correctly!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_llamacpp()