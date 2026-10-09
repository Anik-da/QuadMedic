import logging
import requests
import json
import os
from backend.app.config import GEMINI_API_KEY, HF_TOKEN

logger = logging.getLogger("quadmedic.ai.chatbot")

# Custom response database for the medical chatbot fallback
MEDICAL_RESPONSES = [
    {"keywords": ["burn", "scald"], "response": "For minor burns: Immediately run cool (not cold) water over the burn for 10-15 minutes. Remove tight items. Do not pop blisters. Apply aloe vera gel or a sterile dressing."},
    {"keywords": ["bleed", "wound", "cut"], "response": "To stop bleeding: Apply direct pressure to the wound with a clean cloth or bandage. Elevate the injured area above the heart if possible. Clean with soap and water once bleeding stops."},
    {"keywords": ["choke", "choking"], "response": "If someone is choking and cannot speak: Perform abdominal thrusts (Heimlich maneuver). Stand behind the person, wrap arms around waist, make a fist above the navel, and pull quickly upward and inward."},
    {"keywords": ["fracture", "broken bone"], "response": "Keep the injured limb still. Do not try to realign the bone. Apply a cold pack wrapped in a cloth to reduce swelling. Call emergency services immediately."},
    {"keywords": ["reminder", "medicine", "pill", "dose"], "response": "You can schedule medication reminders in the Reminders tab. Make sure to take medicines with water and follow the prescribed schedule (e.g. before or after food)."},
    {"keywords": ["appointment", "book", "doctor", "slot"], "response": "To book an appointment: Navigate to the Appointment tab in the sidebar. Select an available doctor, choose your preferred slot, and submit the booking request. You can track your position in the queue live."},
    {"keywords": ["hospital", "clinic", "nearest", "emergency info"], "response": "The campus clinic is open 24/7 in the Admin block (Room 102). For emergencies, call the campus ambulance at 9999-555 or use the 'RED ALERT' trigger in your dashboard."},
    {"keywords": ["hello", "hi", "hey", "greetings"], "response": "Hello! I am your QuadMedic AI Health Assistant. How can I help you today? You can ask me about symptoms, first aid guidelines, medicine usage, or appointment booking."}
]


def _get_access_token():
    """Get access token from Cloud Run metadata server (GCP ADC)."""
    try:
        r = requests.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
            timeout=2
        )
        if r.status_code == 200:
            return r.json().get("access_token")
    except Exception:
        pass
    return None


def call_vertex_gemini(prompt: str) -> str:
    """Call Gemini via Vertex AI (uses Cloud Run service account credentials)."""
    project_id = "quad-medic"
    region = "us-central1"
    model = "gemini-2.0-flash-001"
    
    url = f"https://{region}-aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/{region}/publishers/google/models/{model}:generateContent"
    
    access_token = _get_access_token()
    if not access_token:
        raise ValueError("Could not get Cloud Run access token")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 200,
            "temperature": 0.7,
            "topP": 0.95
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
        ]
    }
    
    res = requests.post(url, headers=headers, json=payload, timeout=15)
    res.raise_for_status()
    data = res.json()
    
    candidates = data.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        if parts:
            return parts[0].get("text", "").strip()
    return ""


def call_gemini_api_key(prompt: str) -> str:
    """Call Google Gemini via API key (Google AI Studio / Generative Language API)."""
    if not GEMINI_API_KEY:
        raise ValueError("No GEMINI_API_KEY configured")
    
    models = ["gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"]
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 300,
            "temperature": 0.7,
            "topP": 0.95
        }
    }
    
    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            res = requests.post(url, headers=headers, json=payload, timeout=12)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "").strip()
                        if text:
                            return text
            else:
                logger.warning(f"Gemini model {model} returned status {res.status_code}")
        except Exception as e:
            logger.warning(f"Error calling Gemini model {model}: {e}")
            
    return ""


def call_gemini(prompt: str) -> str:
    """Try configured API key first, then Vertex AI fallback."""
    # Try API key method (primary)
    try:
        result = call_gemini_api_key(prompt)
        if result:
            return result
    except Exception as e:
        logger.warning(f"API key Gemini call failed: {e}")

    # Try Vertex AI (uses service account on Cloud Run)
    try:
        result = call_vertex_gemini(prompt)
        if result:
            return result
    except Exception as e:
        logger.warning(f"Vertex AI call failed: {e}")
    
    return ""


HF_MODELS = [
    "HuggingFaceH4/zephyr-7b-beta",
    "meta-llama/Llama-3.3-70B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct"
]


def call_huggingface_chat(messages: list[dict]) -> str:
    """Send chat messages to Hugging Face Inference Router API with model fallbacks."""
    if not HF_TOKEN:
        logger.warning("HF_TOKEN is not configured.")
        return ""

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    
    url = "https://router.huggingface.co/v1/chat/completions"
    
    for model in HF_MODELS:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 150,
            "temperature": 0.7
        }
        try:
            logger.info(f"Attempting Hugging Face chat completion with model: {model}")
            res = requests.post(url, headers=headers, json=payload, timeout=12)
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"].strip()
                logger.info(f"Successfully generated chat response from model: {model}")
                return content
            else:
                logger.warning(f"Hugging Face model {model} returned status code {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"Error calling Hugging Face model {model}: {e}")
            
    return ""


def generate_chat_response(user_message: str, history: list[dict] = None) -> str:
    user_message_lower = user_message.lower().strip()
    history = history or []

    system_prompt = (
        "You are QuadMedic's AI Clinical Copilot, a highly knowledgeable campus healthcare assistant. "
        "Provide clear, professional, and practical medical advice or first aid instructions. "
        "Always recommend consulting a professional for serious symptoms. Keep answers under 4 sentences. "
        "Be warm, empathetic, and specific in your advice."
    )

    # 1. Primary: Google Gemini AI
    try:
        context = f"System Instructions: {system_prompt}\n\n"
        for turn in history[-3:]:
            role = turn.get("role")
            content = turn.get("content", "")
            if role == "user":
                context += f"Student: {content}\n"
            else:
                context += f"QuadMedic AI: {content}\n"
        context += f"Student: {user_message}\nQuadMedic AI:"
        
        response = call_gemini(context)
        if response:
            return response
    except Exception as e:
        logger.error(f"Error calling Google Gemini AI: {e}")

    # 2. Secondary: Hugging Face Router Fallback
    try:
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history[-3:]:
            role = "assistant" if turn.get("role") != "user" else "user"
            messages.append({"role": role, "content": turn.get("content", "")})
        messages.append({"role": "user", "content": user_message})
        
        response = call_huggingface_chat(messages)
        if response:
            return response
    except Exception as e:
        logger.error(f"Error calling Hugging Face chat: {e}")

    # 3. Fallback: Keyword matcher
    for entry in MEDICAL_RESPONSES:
        for kw in entry["keywords"]:
            if kw in user_message_lower:
                return entry["response"]
                
    if "fever" in user_message_lower:
        return "For mild fevers, ensure adequate rest and hydration. You can take paracetamol (acetaminophen) as directed. If the fever stays above 103°F (39.4°C) or is accompanied by a stiff neck, seek medical attention immediately."
    elif "stomach" in user_message_lower or "diarrhea" in user_message_lower:
        return "Stomach upsets are often caused by viral infections or indigestion. Stay hydrated with electrolytes (ORS), eat bland foods (rice, bananas, applesauce), and avoid dairy or fatty foods."
    
    return "I understand your concern. As an AI health assistant, I recommend maintaining a symptom log. If you are feeling unwell, you can use the AI Symptom Analyzer or schedule a direct consultation with our campus doctor."
