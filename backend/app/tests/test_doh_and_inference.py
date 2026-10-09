import sys
import os

# Add the workspace root to sys.path so we can import backend packages
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Apply the DoH resolver monkeypatch
import backend.app.doh_resolver

from backend.app.ai.medical_chatbot import generate_chat_response
from backend.app.ai.symptom_analyzer import analyze_symptoms

def test_dns_patch():
    print("=== Testing socket.getaddrinfo monkeypatch ===")
    import socket
    try:
        res = socket.getaddrinfo("router.huggingface.co", 443)
        print("Successfully resolved router.huggingface.co via custom DoH:")
        for r in res:
            print(f"  {r}")
        assert len(res) > 0, "No IP address returned"
    except Exception as e:
        print("Failed to resolve via monkeypatch:", e)
        raise e

def test_chatbot():
    print("\n=== Testing generate_chat_response ===")
    user_msg = "Hello, I have a cut on my hand. What first aid should I perform?"
    try:
        response = generate_chat_response(user_msg, history=[])
        print("Chatbot Response:")
        print(response)
        assert len(response) > 0, "Chatbot response is empty"
    except Exception as e:
        print("Failed to get chatbot response:", e)
        raise e

def test_symptom_analyzer():
    print("\n=== Testing analyze_symptoms ===")
    symptoms = "I have sudden severe chest pain spreading to my left arm."
    try:
        result = analyze_symptoms(symptoms)
        print("Symptom Analysis Result:")
        import json
        print(json.dumps(result, indent=2))
        assert "category" in result, "Result missing 'category'"
        assert "risk_level" in result, "Result missing 'risk_level'"
        assert result["emergency"] == True, "Chest pain should be classified as emergency"
    except Exception as e:
        print("Failed to analyze symptoms:", e)
        raise e

if __name__ == "__main__":
    test_dns_patch()
    test_chatbot()
    test_symptom_analyzer()
    print("\nAll tests completed successfully!")
