import logging
import requests
import json
from backend.app.config import USE_REAL_AI_MODELS, HF_TOKEN, GEMINI_API_KEY

logger = logging.getLogger("quadmedic.ai.symptoms")

# Attempt loading model
classifier = None
if USE_REAL_AI_MODELS:
    try:
        from transformers import pipeline
        logger.info("Loading facebook/bart-large-mnli symptom classifier...")
        classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        logger.info("facebook/bart-large-mnli loaded successfully.")
    except Exception as e:
        logger.warning(f"Could not load facebook/bart-large-mnli model: {e}. Falling back to rule-based analyzer.")


def _get_access_token():
    """Get access token from Cloud Run metadata server."""
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


def call_gemini_classify(symptoms_text: str) -> dict:
    """Use Gemini via Vertex AI to classify symptoms."""
    project_id = "quad-medic"
    region = "us-central1"
    model = "gemini-2.0-flash-001"
    
    prompt = f"""You are a medical triage AI. Analyze the following patient symptoms and respond ONLY with valid JSON (no markdown, no explanation).

Symptoms: "{symptoms_text}"

Respond with this exact JSON structure:
{{
  "category": "<one of: Cardiovascular, Respiratory, Infectious Disease, Gastrointestinal, Neurological, Musculoskeletal, Dermatological, General>",
  "conditions": ["<most likely condition 1>", "<most likely condition 2>", "<most likely condition 3>"],
  "confidence": <float between 0.0 and 1.0>,
  "risk_level": "<one of: Low, Medium, High, Critical>",
  "severity": "<one of: Low, Medium, High, Severe>",
  "actions": ["<recommended action 1>", "<recommended action 2>", "<recommended action 3>"],
  "emergency": <true or false>
}}"""

    # Try Vertex AI first
    access_token = _get_access_token()
    if access_token:
        url = f"https://{region}-aiplatform.googleapis.com/v1beta1/projects/{project_id}/locations/{region}/publishers/google/models/{model}:generateContent"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": 400,
                "temperature": 0.3,
                "topP": 0.9
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
                raw_text = parts[0].get("text", "").strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[-1]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3].strip()
                return json.loads(raw_text)
    
    # Try API key method (primary)
    if GEMINI_API_KEY:
        models = ["gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"]
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 400, "temperature": 0.3, "topP": 0.9}
        }
        for model_name in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
                res = requests.post(url, headers=headers, json=payload, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            raw_text = parts[0].get("text", "").strip()
                            if raw_text.startswith("```"):
                                raw_text = raw_text.split("\n", 1)[-1]
                                if raw_text.endswith("```"):
                                    raw_text = raw_text[:-3].strip()
                            return json.loads(raw_text)
            except Exception as e:
                logger.warning(f"Gemini model {model_name} classification error: {e}")
    
    raise ValueError("No Gemini endpoint available")


def call_huggingface_classify(symptoms_text: str) -> dict:
    """Classify symptoms using Hugging Face Zero-Shot Classification API."""
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN is not configured")
        
    url = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-mnli"
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 1. Determine medical category
    categories = ["Cardiovascular", "Respiratory", "Infectious Disease", "Gastrointestinal", "Neurological", "Musculoskeletal", "Dermatological", "General"]
    payload = {
        "inputs": symptoms_text,
        "parameters": {"candidate_labels": categories}
    }
    
    res = requests.post(url, headers=headers, json=payload, timeout=10)
    res.raise_for_status()
    cat_data = res.json()
    
    # Check if response is a list or dict
    if isinstance(cat_data, list) and len(cat_data) > 0:
        # It's a list of {"label": ..., "score": ...} dicts
        cat_data.sort(key=lambda x: x.get("score", 0), reverse=True)
        primary_category = cat_data[0]["label"]
        confidence = round(cat_data[0]["score"], 2)
    elif isinstance(cat_data, dict) and "labels" in cat_data:
        primary_category = cat_data["labels"][0]
        confidence = round(cat_data["scores"][0], 2)
    else:
        raise ValueError("Unexpected response format from HF classifier")
    
    # 2. Determine risk level
    risk_labels = ["Low", "Medium", "High", "Critical"]
    payload_risk = {
        "inputs": symptoms_text,
        "parameters": {"candidate_labels": risk_labels}
    }
    res_risk = requests.post(url, headers=headers, json=payload_risk, timeout=10)
    res_risk.raise_for_status()
    risk_data = res_risk.json()
    
    if isinstance(risk_data, list) and len(risk_data) > 0:
        risk_data.sort(key=lambda x: x.get("score", 0), reverse=True)
        risk_level = risk_data[0]["label"]
    elif isinstance(risk_data, dict) and "labels" in risk_data:
        risk_level = risk_data["labels"][0]
    else:
        raise ValueError("Unexpected risk response format from HF classifier")
    
    # Formulate actions based on category & risk
    actions = ["Consult with the campus healthcare center."]
    if risk_level in ["Critical", "High"]:
        actions = [
            "Seek urgent medical attention at the nearest emergency room.",
            "Sit down, remain calm, and avoid physical exertion.",
            "Contact the campus emergency team immediately."
        ]
    else:
        actions.extend([
            "Ensure adequate hydration and rest.",
            "Monitor symptoms over the next 24-48 hours."
        ])
        
    return {
        "category": primary_category,
        "conditions": [f"Potential {primary_category} issue"],
        "confidence": confidence,
        "risk_level": risk_level,
        "severity": "High" if risk_level in ["Critical", "High"] else ("Medium" if risk_level == "Medium" else "Low"),
        "actions": actions,
        "emergency": risk_level == "Critical"
    }



# Heuristics for realistic responses in fallback mode
DISEASE_DATABASE = {
    "chest pain": {
        "conditions": ["Angina", "Myocardial Infarction (Heart Attack)", "Costochondritis"],
        "severity": "Severe", "risk_level": "Critical",
        "actions": ["CALL 911 / AMBULANCE IMMEDIATELY", "Sit down and stay calm", "Take prescribed nitroglycerin if available"],
        "emergency": True
    },
    "difficulty breathing": {
        "conditions": ["Asthma Attack", "Pneumonia", "Anaphylaxis (Severe Allergy)"],
        "severity": "Severe", "risk_level": "Critical",
        "actions": ["Use rescue inhaler immediately", "Seek emergency medical help", "Sit upright and loosen tight clothing"],
        "emergency": True
    },
    "loss of consciousness": {
        "conditions": ["Syncope", "Severe Hypoglycemia", "Stroke"],
        "severity": "Severe", "risk_level": "Critical",
        "actions": ["Lay the person flat on their back", "Check for breathing and pulse", "Call campus emergency team"],
        "emergency": True
    },
    "high fever": {
        "conditions": ["Influenza", "Meningitis", "Severe Viral/Bacterial Infection"],
        "severity": "High", "risk_level": "High",
        "actions": ["Take antipyretics like paracetamol", "Stay hydrated", "Seek doctor consultation if above 103°F (39.4°C)"],
        "emergency": True
    },
    "seizures": {
        "conditions": ["Epileptic Seizure", "High-Fever Convulsion (Febrile Seizure)", "Neurological Event"],
        "severity": "Severe", "risk_level": "Critical",
        "actions": ["Clear the surrounding area of sharp objects", "Do not hold the person down", "Time the seizure and call ambulance"],
        "emergency": True
    },
    "cough": {
        "conditions": ["Common Cold", "Bronchitis", "Allergic Rhinitis"],
        "severity": "Low", "risk_level": "Low",
        "actions": ["Drink warm fluids", "Rest and get plenty of sleep", "Use OTC cough syrup or lozenges"],
        "emergency": False
    },
    "headache": {
        "conditions": ["Tension Headache", "Migraine", "Dehydration Headache"],
        "severity": "Medium", "risk_level": "Medium",
        "actions": ["Rest in a dark, quiet room", "Drink plenty of water", "Take ibuprofen or acetaminophen if pain persists"],
        "emergency": False
    },
    "stomach pain": {
        "conditions": ["Gastroenteritis", "Acid Reflux", "Irritable Bowel Syndrome"],
        "severity": "Medium", "risk_level": "Medium",
        "actions": ["Avoid heavy or spicy foods", "Drink chamomile tea", "Seek doctor if localized in lower right abdomen (Appendicitis)"],
        "emergency": False
    }
}

def analyze_symptoms(symptoms_text: str) -> dict:
    symptoms_text_lower = symptoms_text.lower()
    
    critical_triggers = ["chest pain", "difficulty breathing", "shortness of breath", "loss of consciousness", 
                         "passed out", "high fever", "seizure", "seizures", "fit", "fits"]
    is_emergency = any(trigger in symptoms_text_lower for trigger in critical_triggers)
    
    # Try Gemini API first (works on Cloud Run via Vertex AI)
    try:
        result = call_gemini_classify(symptoms_text)
        if is_emergency:
            result["emergency"] = True
        return result
    except Exception as e:
        logger.error(f"Error during Gemini classification: {e}. Trying Hugging Face classifier fallback.")

    # Try Hugging Face Serverless Classifier Fallback
    try:
        result = call_huggingface_classify(symptoms_text)
        if is_emergency:
            result["emergency"] = True
            result["risk_level"] = "Critical"
            result["severity"] = "Severe"
        return result
    except Exception as e:
        logger.error(f"Error during Hugging Face Serverless classification: {e}. Trying local/heuristic fallback.")

    # If using local HF model (from transformers pipeline)
    if classifier is not None:
        try:
            categories = ["Cardiovascular", "Respiratory", "Infectious Disease", "Gastrointestinal", "Neurological", "Musculoskeletal"]
            res = classifier(symptoms_text, candidate_labels=categories)
            primary_category = res['labels'][0]
            confidence = res['scores'][0]
            
            risk_labels = ["Low", "Medium", "High", "Critical"]
            risk_res = classifier(symptoms_text, candidate_labels=risk_labels)
            risk_level = risk_res['labels'][0]
            
            actions = ["Consult the campus healthcare center."]
            if risk_level in ["Critical", "High"]:
                actions = ["Seek urgent medical attention at the nearest emergency room.", "Do not exert yourself physically."]
            else:
                actions.append("Ensure adequate hydration and rest.")
                
            return {
                "category": primary_category,
                "conditions": [f"Potential {primary_category} Condition"],
                "confidence": round(confidence, 2),
                "risk_level": risk_level,
                "severity": "High" if risk_level in ["Critical", "High"] else "Low",
                "actions": actions,
                "emergency": is_emergency or risk_level == "Critical"
            }
        except Exception as e:
            logger.error(f"Error during local model classification: {e}. Using fallback.")

    # Fallback / Heuristic logic
    matched_conditions = []
    highest_severity = "Low"
    highest_risk = "Low"
    recommended_actions = []
    
    for key, data in DISEASE_DATABASE.items():
        if key in symptoms_text_lower:
            matched_conditions.extend(data["conditions"])
            if data["emergency"]:
                is_emergency = True
                highest_severity = "Severe"
                highest_risk = "Critical"
            elif highest_risk != "Critical" and data["risk_level"] == "High":
                highest_severity = "High"
                highest_risk = "High"
            elif highest_risk not in ["Critical", "High"] and data["risk_level"] == "Medium":
                highest_severity = "Medium"
                highest_risk = "Medium"
            recommended_actions.extend(data["actions"])
            
    if not matched_conditions:
        matched_conditions = ["General Malaise", "Viral Syndrome"]
        highest_severity = "Medium" if is_emergency else "Low"
        highest_risk = "Critical" if is_emergency else "Low"
        recommended_actions = [
            "Monitor body temperature and symptoms",
            "Maintain fluid intake",
            "Visit campus clinic if symptoms persist for more than 48 hours"
        ]
        
    recommended_actions = list(dict.fromkeys(recommended_actions))
    
    return {
        "category": "Infectious / General" if highest_risk in ["Low", "Medium"] else "Emergency Medicine",
        "conditions": matched_conditions[:3],
        "confidence": 0.88,
        "risk_level": highest_risk,
        "severity": highest_severity,
        "actions": recommended_actions,
        "emergency": is_emergency
    }
