import logging
import numpy as np
from backend.app.config import USE_REAL_AI_MODELS

logger = logging.getLogger("quadmedic.ai.risk")

# Attempt loading sentence transformers
model = None
if USE_REAL_AI_MODELS:
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformers/all-MiniLM-L6-v2...")
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        logger.info("SentenceTransformer loaded successfully.")
    except Exception as e:
        logger.warning(f"Could not load SentenceTransformer: {e}. Using TF-IDF/heuristic keyword embedding matching.")

# Reference symptom statements for semantic matching
SEVERE_REF = "I have severe crushing chest pain, difficulty breathing, feeling faint, seizures, or lost consciousness."
MILD_REF = "I have a mild stuffy nose, scratchy throat, minor cough, or slight fatigue."

def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    if not height_cm:
        return 0.0
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m ** 2), 1)

def get_symptom_severity_score(symptoms_text: str) -> float:
    """Returns a score between 0.0 (very mild) and 1.0 (extremely severe)"""
    if not symptoms_text or symptoms_text.strip().lower() in ["none", "no symptoms"]:
        return 0.0
        
    symptoms_lower = symptoms_text.lower()
    
    # Check if we can use sentence transformer
    if model is not None:
        try:
            embeddings = model.encode([symptoms_text, SEVERE_REF, MILD_REF])
            # Compute cosine similarities
            # emb[0]: input, emb[1]: severe, emb[2]: mild
            sim_severe = np.dot(embeddings[0], embeddings[1]) / (np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1]))
            sim_mild = np.dot(embeddings[0], embeddings[2]) / (np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[2]))
            
            # Map similarity to score
            # Higher similarity to severe increases the score
            diff = sim_severe - sim_mild
            # Map [-1.0, 1.0] to [0.0, 1.0]
            score = (diff + 1.0) / 2.0
            return float(np.clip(score, 0.0, 1.0))
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}. Using keywords.")

    # Fallback keyword-based severity scoring
    severe_keywords = ["chest pain", "breathing", "breath", "unconscious", "passed out", "seizure", "seizures", "fever", "severe", "crushing", "paralyzed"]
    moderate_keywords = ["headache", "stomach", "pain", "vomiting", "nausea", "dizzy", "fatigue", "throat", "swelling"]
    
    score = 0.1 # Base mild score
    
    # Count severe keyword hits
    severe_hits = sum(1 for kw in severe_keywords if kw in symptoms_lower)
    mod_hits = sum(1 for kw in moderate_keywords if kw in symptoms_lower)
    
    score += severe_hits * 0.3
    score += mod_hits * 0.1
    
    return float(np.clip(score, 0.0, 1.0))

def predict_health_risk(
    age: int,
    weight_kg: float,
    height_cm: float,
    sleep_hours: float,
    water_intake_l: float,
    activity_level: str, # "Sedentary", "Active", "Very Active"
    symptoms: str
) -> dict:
    # Calculate BMI
    bmi = calculate_bmi(weight_kg, height_cm)
    
    # Start with a base health score of 100
    health_score = 100.0
    
    # 1. BMI Penalty
    if bmi < 18.5: # Underweight
        health_score -= (18.5 - bmi) * 4
    elif bmi > 24.9: # Overweight / Obese
        health_score -= (bmi - 24.9) * 3
        
    # 2. Sleep Penalty
    # Ideal sleep is 7-9 hours
    if sleep_hours < 7:
        health_score -= (7 - sleep_hours) * 6
    elif sleep_hours > 9:
        health_score -= (sleep_hours - 9) * 3
        
    # 3. Water Intake Penalty
    # Ideal is 2.5 - 3.5 liters
    if water_intake_l < 2.5:
        health_score -= (2.5 - water_intake_l) * 8
        
    # 4. Activity Penalty
    if activity_level.lower() == "sedentary":
        health_score -= 10
    elif activity_level.lower() == "very active":
        health_score += 2 # Slight bonus
        
    # 5. Symptom Penalty
    severity_score = get_symptom_severity_score(symptoms)
    # Deduct up to 45 points based on symptom severity
    health_score -= severity_score * 45
    
    # Bound health score between 0 and 100
    health_score = max(0.0, min(100.0, health_score))
    health_score = round(health_score, 1)
    
    # Determine risk category
    if health_score >= 85:
        risk_category = "Low"
    elif health_score >= 65:
        risk_category = "Medium"
    elif health_score >= 45:
        risk_category = "High"
    else:
        risk_category = "Critical"
        
    # Overwrite category to Critical if symptoms trigger immediate emergency
    symptoms_lower = symptoms.lower()
    critical_triggers = ["chest pain", "difficulty breathing", "shortness of breath", "loss of consciousness", "passed out", "seizure", "seizures"]
    if any(trigger in symptoms_lower for trigger in critical_triggers):
        risk_category = "Critical"
        # Force lower score
        health_score = min(health_score, 30.0)
        
    return {
        "health_score": health_score,
        "bmi": bmi,
        "symptom_severity": round(severity_score, 2),
        "risk_category": risk_category
    }
