import logging
from backend.app.config import USE_REAL_AI_MODELS

logger = logging.getLogger("quadmedic.ai.wellness")

# Attempt loading emotion classifier
classifier = None
if USE_REAL_AI_MODELS:
    try:
        from transformers import pipeline
        logger.info("Loading j-hartmann/emotion-english-distilroberta-base model...")
        classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base")
        logger.info("Emotion model loaded successfully.")
    except Exception as e:
        logger.warning(f"Could not load emotion model: {e}. Falling back to keyword-based emotion analyzer.")

# Wellness advice dictionary based on emotion
WELLNESS_ADVICE = {
    "happy": [
        "That's wonderful! Keep doing what makes you happy.",
        "Consider sharing your positive energy with friends or peers today.",
        "Take a moment to practice gratitude for the good things in your day."
    ],
    "neutral": [
        "A calm, neutral state is great for focus. What are your plans today?",
        "Remember to take short stretch breaks if you are studying or working.",
        "Taking a brief walk outside can help maintain this balanced state."
    ],
    "stress": [
        "Stress can be challenging. Take 3 deep, slow breaths right now.",
        "Try the 4-7-8 breathing technique: inhale for 4s, hold for 7s, exhale for 8s.",
        "Prioritize your tasks and tackle them one step at a time. Do not hesitate to delegate or ask for help."
    ],
    "anxiety": [
        "Anxiety can feel overwhelming. Focus on what you can control right now.",
        "Try the 5-4-3-2-1 grounding exercise: Identify 5 things you see, 4 you feel, 3 you hear, 2 you smell, and 1 you taste.",
        "Reduce caffeine intake and talk to a trusted friend or counselor."
    ],
    "sadness": [
        "It's completely okay to feel sad. Allow yourself to experience your emotions without judgment.",
        "Consider reaching out to a friend or the campus wellness counselor to talk things through.",
        "Do something gentle for yourself, like listening to calming music or having a warm cup of tea."
    ],
    "anger": [
        "Anger is a natural emotion. Try to step away from the situation for a few minutes.",
        "Physical movement (like walking or running) can help release pent-up energy.",
        "Write down what's making you angry on a piece of paper, then shred it to release the tension."
    ]
}

def analyze_emotion(text: str) -> dict:
    if not text or not text.strip():
        return {
            "emotion": "neutral",
            "score": 1.0,
            "suggestions": WELLNESS_ADVICE["neutral"]
        }

    text_lower = text.lower()
    
    # If using real model
    if classifier is not None:
        try:
            res = classifier(text)
            # j-hartmann outputs labels like: joy, sadness, fear, anger, surprise, disgust, neutral
            label_raw = res[0]['label'].lower()
            score = res[0]['score']
            
            # Map raw labels to standard categories
            mapping = {
                "joy": "happy",
                "fear": "anxiety",
                "surprise": "happy",
                "disgust": "stress",
                "anger": "anger",
                "sadness": "sadness",
                "neutral": "neutral"
            }
            mapped_emotion = mapping.get(label_raw, "neutral")
            
            # If the user directly mentions stress in text, override if it was neutral
            if "stress" in text_lower or "overwhelmed" in text_lower:
                mapped_emotion = "stress"
                
            return {
                "emotion": mapped_emotion,
                "score": round(score, 2),
                "suggestions": WELLNESS_ADVICE.get(mapped_emotion, WELLNESS_ADVICE["neutral"])
            }
        except Exception as e:
            logger.error(f"Error classifying emotion: {e}. Using fallback.")

    # Fallback keyword analyzer
    detected_emotion = "neutral"
    
    keywords = {
        "happy": ["happy", "good", "great", "glad", "joy", "excited", "wonderful", "amazing", "smile", "love"],
        "sadness": ["sad", "depressed", "unhappy", "cry", "crying", "lonely", "grief", "down", "blue", "lost"],
        "anxiety": ["anxious", "anxiety", "worry", "worried", "scared", "fear", "panic", "nervous", "dread"],
        "stress": ["stress", "stressed", "overwhelmed", "pressure", "tired", "exhausted", "burnout", "busy"],
        "anger": ["angry", "mad", "furious", "hate", "irritated", "annoyed", "pissed"]
    }
    
    scores = {k: 0 for k in keywords}
    for emotion, kws in keywords.items():
        for kw in kws:
            if kw in text_lower:
                scores[emotion] += 1
                
    max_emotion = max(scores, key=scores.get)
    if scores[max_emotion] > 0:
        detected_emotion = max_emotion
        score = 0.85
    else:
        detected_emotion = "neutral"
        score = 1.0
        
    return {
        "emotion": detected_emotion,
        "score": score,
        "suggestions": WELLNESS_ADVICE.get(detected_emotion, WELLNESS_ADVICE["neutral"])
    }
