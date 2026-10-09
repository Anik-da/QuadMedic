import logging
from backend.app.config import USE_REAL_AI_MODELS

logger = logging.getLogger("quadmedic.ai.insights")

# Attempt loading Flan-T5
tokenizer = None
model = None
if USE_REAL_AI_MODELS:
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        logger.info("Loading google/flan-t5-base model...")
        tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-base")
        model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-base")
        logger.info("google/flan-t5-base loaded successfully.")
    except Exception as e:
        logger.warning(f"Could not load Flan-T5: {e}. Using rule-based insights generator.")

def generate_health_insights(
    sleep_hours: float,
    water_intake_l: float,
    activity_level: str,
    symptoms: str,
    emotion: str
) -> list[str]:
    # If using real model
    if model is not None and tokenizer is not None:
        try:
            prompt = (
                f"Context: Student health profile:\n"
                f"- Sleep: {sleep_hours} hours (Ideal: 7-9)\n"
                f"- Water: {water_intake_l} liters (Ideal: 2.5-3.5)\n"
                f"- Activity: {activity_level}\n"
                f"- Symptoms: {symptoms or 'None'}\n"
                f"- Emotion: {emotion or 'Neutral'}\n"
                f"Task: Generate 3 bullet points of highly specific, professional medical and wellness advice for this student."
            )
            inputs = tokenizer(prompt, return_tensors="pt")
            outputs = model.generate(**inputs, max_length=200)
            text_out = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Post-process Flan-T5 output to lines
            lines = [line.strip().replace("- ", "").replace("* ", "") for line in text_out.split("\n") if line.strip()]
            if len(lines) >= 2:
                return lines
        except Exception as e:
            logger.error(f"Error during Flan-T5 generation: {e}. Using fallback.")

    # Rule-based generator (produces very clean, highly relevant lists)
    insights = []
    
    # 1. Sleep advice
    if sleep_hours < 6:
        insights.append(f"Your sleep of {sleep_hours}h is severely low. Aim for 7-8 hours to allow brain and muscle recovery.")
    elif sleep_hours < 7:
        insights.append("Try to increase your sleep by 30-60 minutes. Establish a winding-down routine without screens.")
    else:
        insights.append("Great job maintaining a healthy sleep schedule! Consistency is key for academic focus.")
        
    # 2. Water advice
    if water_intake_l < 2.0:
        insights.append(f"Dehydration danger: your {water_intake_l}L daily intake is low. Keep a water bottle on your desk and aim for 2.5L+.")
    elif water_intake_l < 2.8:
        insights.append("Consider drinking one extra glass of water in the morning and afternoon to optimize hydration.")
    else:
        insights.append("Excellent hydration! Drinking sufficient water supports metabolism and kidney function.")
        
    # 3. Activity advice
    if activity_level.lower() == "sedentary":
        insights.append("Sedentary lifestyle warning: Schedule a 15-minute walk between classes or lectures to boost cardiovascular health.")
    elif activity_level.lower() == "active":
        insights.append("Good physical activity level. Mix in some light strength training or stretching to prevent study fatigue.")
    else:
        insights.append("Superb activity level! Make sure you refuel with adequate proteins and electrolytes.")
        
    # 4. Symptoms adjustment
    if symptoms and symptoms.lower().strip() not in ["none", "no symptoms"]:
        insights.append(f"Monitor the symptoms '{symptoms}' closely. Avoid heavy physical strain and rest.")
        
    # 5. Emotion advice
    if emotion.lower() in ["stress", "anxiety"]:
        insights.append("Elevated stress/anxiety detected: Dedicate 5 minutes to mindfulness exercises or visit the campus wellness room.")
    elif emotion.lower() == "sadness":
        insights.append("Feeling down can impact physical energy. Engage in social activities or speak to a student counselor.")
        
    return insights[:4]
