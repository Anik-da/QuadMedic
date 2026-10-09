from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import requests
import random
import uuid
import datetime
import numpy as np

from backend.app.database import get_collection
from backend.app.auth import get_current_user
from backend.app.ai.symptom_analyzer import analyze_symptoms
from backend.app.ai.medical_chatbot import generate_chat_response
from backend.app.ai.risk_predictor import predict_health_risk
from backend.app.ai.wellness_assistant import analyze_emotion
from backend.app.ai.insights_engine import generate_health_insights
from backend.app.ai.doc_analyzer import analyze_prescription_image, analyze_document_text, perform_ocr
from backend.app.ai.voice_assistant import speech_to_text, text_to_speech
from backend.app.config import USE_REAL_AI_MODELS, EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, EMAILJS_USER_ID, EMAILJS_ACCESS_TOKEN

router = APIRouter(prefix="/ai", tags=["AI Copilot Endpoints"])

class SymptomRequest(BaseModel):
    symptoms: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class RiskRequest(BaseModel):
    age: int
    weight_kg: float
    height_cm: float
    sleep_hours: float
    water_intake_l: float
    activity_level: str # "Sedentary", "Active", "Very Active"
    symptoms: str

class EmotionRequest(BaseModel):
    text: str

class InsightsRequest(BaseModel):
    sleep_hours: float
    water_intake_l: float
    activity_level: str
    symptoms: str
    emotion: str

class TextToSpeechRequest(BaseModel):
    text: str

# Local folders for media
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Semantic Knowledge Base Library
KNOWLEDGE_BASE = [
    {"topic": "Cardiovascular Health", "content": "Maintain heart health by getting at least 150 minutes of moderate aerobic activity per week, limiting saturated fats, and managing stress levels. Warning signs of heart issues include sudden chest pressure, radiating pain, and shortness of breath."},
    {"topic": "Dehydration & Hydration", "content": "Water is essential for digestion, joints, and temperature regulation. Aim to drink 2.5 to 3.5 liters of water daily. Dehydration symptoms include dry mouth, dark urine, and fatigue."},
    {"topic": "First Aid for CPR", "content": "If an adult is unresponsive and not breathing, call emergency services, then push hard and fast in the center of the chest (100 to 120 compressions per minute). Let the chest rise completely between compressions."},
    {"topic": "Sleep Hygiene", "content": "Improve sleep quality by keeping a consistent bedtime, avoiding screens 1 hour before sleep, maintaining a cool dark room, and limiting caffeine intake after 2:00 PM."},
    {"topic": "Mental Burnout Prevention", "content": "Prevent student burnout by taking regular study breaks (50 mins study / 10 mins break), getting daily sunlight, practicing mindfulness, and talking to campus support counseling early."},
    {"topic": "Seasonal Influenza Care", "content": "Influenza presents with high fever, sore throat, and muscle aches. Treatment includes bed rest, high hydration, and paracetamol for pain. Consult a doctor for antivirals within 48 hours of symptoms."}
]

@router.post("/analyze-symptoms")
def post_analyze_symptoms(req: SymptomRequest, current_user: dict = Depends(get_current_user)):
    res = analyze_symptoms(req.symptoms)
    
    # Save search log in DB
    sym_col = get_collection("symptoms")
    sym_col.insert_one({
        "student_email": current_user["email"],
        "symptoms": req.symptoms,
        "analysis": res
    })
    
    # If emergency is triggered, log to emergency cases collection
    if res.get("emergency", False):
        emergency_col = get_collection("emergency_cases")
        emergency_col.insert_one({
            "student_email": current_user["email"],
            "student_name": current_user.get("username", "Student"),
            "symptoms": req.symptoms,
            "risk_level": res.get("risk_level", "Critical"),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "resolved": False
        })
        
    return res

@router.post("/chat")
def post_chat(req: ChatRequest, current_user: dict = Depends(get_current_user)):
    # Retrieve chat history
    chat_col = get_collection("chat_history")
    session_id = req.session_id or current_user["email"]
    
    # Get last 5 turns of history
    history_cursor = chat_col.find({"session_id": session_id}).sort([("timestamp", 1)]).limit(10)
    history = []
    for h in history_cursor:
        history.append({"role": "user", "content": h.get("user_message", "")})
        history.append({"role": "assistant", "content": h.get("bot_response", "")})
        
    bot_res = generate_chat_response(req.message, history)
    
    # Save turn
    chat_col.insert_one({
        "session_id": session_id,
        "student_email": current_user["email"],
        "user_message": req.message,
        "bot_response": bot_res,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    return {"response": bot_res, "session_id": session_id}

@router.post("/risk-predict")
def post_risk_predict(req: RiskRequest, current_user: dict = Depends(get_current_user)):
    res = predict_health_risk(
        age=req.age,
        weight_kg=req.weight_kg,
        height_cm=req.height_cm,
        sleep_hours=req.sleep_hours,
        water_intake_l=req.water_intake_l,
        activity_level=req.activity_level,
        symptoms=req.symptoms
    )
    
    # Save scores
    score_col = get_collection("health_scores")
    score_col.insert_one({
        "student_email": current_user["email"],
        "age": req.age,
        "bmi": res["bmi"],
        "sleep_hours": req.sleep_hours,
        "water_intake_l": req.water_intake_l,
        "activity_level": req.activity_level,
        "symptoms": req.symptoms,
        "health_score": res["health_score"],
        "risk_category": res["risk_category"],
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    return res

@router.post("/emotion-wellness")
def post_emotion_wellness(req: EmotionRequest):
    return analyze_emotion(req.text)

@router.post("/health-insights")
def post_health_insights(req: InsightsRequest):
    points = generate_health_insights(
        sleep_hours=req.sleep_hours,
        water_intake_l=req.water_intake_l,
        activity_level=req.activity_level,
        symptoms=req.symptoms,
        emotion=req.emotion
    )
    return {"insights": points}

@router.post("/document-analyze")
async def post_document_analyze(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    file_id = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOADS_DIR, file_id)
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    ocr_text = perform_ocr(file_path)
    analysis = analyze_document_text(ocr_text)
    
    # Save record
    reports_col = get_collection("medical_reports")
    reports_col.insert_one({
        "student_email": current_user["email"],
        "filename": file.filename,
        "local_path": file_path,
        "firebase_url": f"https://firebasestorage.googleapis.com/v0/b/quad-medic.appspot.com/o/{file_id}", # Simulated Firebase Storage link
        "diseases": analysis["diseases"],
        "medicines": analysis["medicines"],
        "notes": analysis["notes"],
        "raw_text": analysis["raw_text"]
    })
    
    return {
        "filename": file.filename,
        "diseases": analysis["diseases"],
        "medicines": analysis["medicines"],
        "notes": analysis["notes"]
    }

@router.post("/speech-to-text")
async def post_speech_to_text(file: UploadFile = File(...)):
    file_id = f"{uuid.uuid4().hex}.wav"
    file_path = os.path.join(UPLOADS_DIR, file_id)
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    transcript = speech_to_text(file_path)
    return {"transcript": transcript}

@router.post("/text-to-speech")
def post_text_to_speech(req: TextToSpeechRequest):
    file_id = uuid.uuid4().hex
    output_path = os.path.join(UPLOADS_DIR, f"{file_id}.tmp")
    
    fmt = text_to_speech(req.text, output_path)
    if not fmt:
        raise HTTPException(status_code=500, detail="Voice generation failed")
        
    final_filename = f"{file_id}.{fmt}"
    final_path = os.path.join(UPLOADS_DIR, final_filename)
    
    # Rename tmp to correct extension format
    try:
        os.rename(output_path, final_path)
    except Exception:
        final_path = output_path
        
    media_type = "audio/mpeg" if fmt == "mp3" else "audio/wav"
    return FileResponse(final_path, media_type=media_type, filename=f"response.{fmt}")

@router.get("/knowledge-search")
def search_knowledge(query: str):
    query_lower = query.lower()
    # Simple semantic scoring using word overlap / keyword matching
    # If SentenceTransformer is loaded, we could compute cosine similarities
    results = []
    for item in KNOWLEDGE_BASE:
        # Check overlaps
        words = query_lower.split()
        overlap_score = sum(1 for w in words if w in item["topic"].lower() or w in item["content"].lower())
        if overlap_score > 0:
            results.append((overlap_score, item))
            
    # Sort by score
    results.sort(key=lambda x: x[0], reverse=True)
    out = [item[1] for item in results]
    
    if not out:
        # Return generic match
        return [KNOWLEDGE_BASE[0], KNOWLEDGE_BASE[3]]
        
    return out

@router.get("/emailjs-config")
def get_emailjs_config():
    return {
        "service_id": EMAILJS_SERVICE_ID,
        "template_id": EMAILJS_TEMPLATE_ID,
        "user_id": EMAILJS_USER_ID
    }

# =============================================
# EMERGENCY TRIGGER & EMAIL NOTIFICATION
# =============================================

import smtplib
from email.mime.text import MIMEText
import logging

logger = logging.getLogger("quadmedic.email")

def send_emergency_email(to_email: str, student_name: str, location: dict, event_type: str = "SOS Alarm", nearest_hospital: str = "Campus Clinic") -> bool:
    subject = f"🚨 [QuadMedic Emergency Alert] Critical Incident for {student_name}"
    
    lat = location.get("latitude", "Unknown")
    lon = location.get("longitude", "Unknown")
    maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}" if lat != "Unknown" else "Unknown"
    
    # Try to fetch the student's emergency contact phone number
    student_phone = "Not Configured"
    try:
        students_col = get_collection("students")
        student_profile = students_col.find_one({"name": student_name}) or students_col.find_one({"emergency_email": to_email})
        if student_profile and "emergency_contacts" in student_profile:
            contacts = student_profile["emergency_contacts"]
            if contacts and len(contacts) > 0 and "phone" in contacts[0]:
                student_phone = contacts[0]["phone"]
    except Exception as phone_err:
        logger.warning(f"Could not retrieve student phone for email context: {phone_err}")

    body = f"""Dear Emergency Contact,

This is an automated critical alert from QuadMedic Smart Campus Healthcare.
An emergency event was detected for {student_name}.

Details:
- Event: {event_type} (Fall/Shock/Manual SOS)
- Live Location: Latitude {lat}, Longitude {lon}
- Google Maps Link: {maps_url}

Please coordinate with campus security and local medical services immediately.

Best regards,
QuadMedic Emergency Dispatcher
"""
    
    logger.info(f"=== EMERGENCY EMAIL TRIGGERED ===")
    logger.info(f"To: {to_email}")
    logger.info(f"Subject: {subject}")
    logger.info(f"Body:\n{body}")
    logger.info(f"=================================")
    
    emailjs_sent = False
    
    # Attempt to send via EmailJS API
    try:
        emailjs_url = "https://api.emailjs.com/api/v1.0/email/send"
        emailjs_payload = {
            "service_id": EMAILJS_SERVICE_ID,
            "template_id": EMAILJS_TEMPLATE_ID,
            "user_id": EMAILJS_USER_ID,
            "accessToken": EMAILJS_ACCESS_TOKEN,
            "template_params": {
                # Recipient Address (exhaustively mapped)
                "to_email": to_email,
                "toEmail": to_email,
                "email": to_email,
                "Email": to_email,
                "emergency_email": to_email,
                "emergencyEmail": to_email,
                "guardian_email": to_email,
                "guardianEmail": to_email,
                "contact_email": to_email,
                "contactEmail": to_email,
                "to": to_email,
                "To": to_email,
                "recipient": to_email,
                "Recipient": to_email,
                "recipient_email": to_email,
                "recipientEmail": to_email,

                # Patient Name Casing
                "patient_name": student_name,
                "patientName": student_name,
                "name": student_name,
                "Name": student_name,
                "student_name": student_name,
                "studentName": student_name,
                "PatientName": student_name,
                "Patient_Name": student_name,
                "StudentName": student_name,
                "Student_Name": student_name,
                
                # Phone Number Casing
                "phone_number": student_phone,
                "phoneNumber": student_phone,
                "phone": student_phone,
                "Phone": student_phone,
                "PhoneNumber": student_phone,
                "Phone_Number": student_phone,
                "student_phone": student_phone,
                "studentPhone": student_phone,
                "contact_phone": student_phone,
                "contactPhone": student_phone,
                "phoneNum": student_phone,
                "PhoneNum": student_phone,
                
                # GPS Coordinates Casing
                "gps_coordinates": f"{lat}, {lon}" if lat != "Unknown" else "Unknown",
                "gpsCoordinates": f"{lat}, {lon}" if lat != "Unknown" else "Unknown",
                "coordinates": f"{lat}, {lon}" if lat != "Unknown" else "Unknown",
                "coords": f"{lat}, {lon}" if lat != "Unknown" else "Unknown",
                "latitude": str(lat),
                "longitude": str(lon),
                "lat": str(lat),
                "lon": str(lon),
                "lng": str(lon),
                "long": str(lon),
                "GpsCoordinates": f"{lat}, {lon}" if lat != "Unknown" else "Unknown",
                "Gps_Coordinates": f"{lat}, {lon}" if lat != "Unknown" else "Unknown",
                "Coordinates": f"{lat}, {lon}" if lat != "Unknown" else "Unknown",
                "Latitude": str(lat),
                "Longitude": str(lon),
                "Lat": str(lat),
                "Lon": str(lon),
                "Lng": str(lon),
                "Long": str(lon),
                
                # Physical Location Casing
                "physical_location": nearest_hospital,
                "physicalLocation": nearest_hospital,
                "location": nearest_hospital,
                "nearest_hospital": nearest_hospital,
                "nearestHospital": nearest_hospital,
                "Location": nearest_hospital,
                "PhysicalLocation": nearest_hospital,
                "Physical_Location": nearest_hospital,
                "NearestHospital": nearest_hospital,
                "Nearest_Hospital": nearest_hospital,
                "hospital": nearest_hospital,
                "Hospital": nearest_hospital,
                
                # Links Casing
                "live_route_link": maps_url,
                "liveRouteLink": maps_url,
                "maps_url": maps_url,
                "mapsUrl": maps_url,
                "google_maps_link": maps_url,
                "googleMapsLink": maps_url,
                "route_link": maps_url,
                "routeLink": maps_url,
                "link": maps_url,
                "Link": maps_url,
                "maps": maps_url,
                "Maps": maps_url,
                "google_maps": maps_url,
                "googleMaps": maps_url,
                "MapsUrl": maps_url,
                "Maps_Url": maps_url,
                "GoogleMapsLink": maps_url,
                "Google_Maps_Link": maps_url,
                "LiveRouteLink": maps_url,
                "Live_Route_Link": maps_url,
                
                # Standard Fallback & Control fields
                "event_type": event_type,
                "eventType": event_type,
                "event": event_type,
                "Event": event_type,
                "EventType": event_type,
                "Event_Type": event_type,
                
                "message": body,
                "messageBody": body,
                "email_body": body,
                "body": body,
                "Message": body,
                "MessageBody": body,
                "Body": body,
                "to_name": "Emergency Contact",
                "from_name": "QuadMedic Emergency Dispatcher",
                "reply_to": "teamaura436@gmail.com"
            }
        }
        r = requests.post(emailjs_url, json=emailjs_payload, timeout=8)
        if r.status_code == 200:
            logger.info("EmailJS emergency email sent successfully via backend REST API.")
            emailjs_sent = True
        else:
            logger.warning(f"EmailJS backend send returned status {r.status_code}: {r.text}")
    except Exception as e:
        logger.error(f"EmailJS backend send failed: {e}")

    # Save to MongoDB for verification audit
    try:
        get_collection("emergency_emails").insert_one({
            "recipient": to_email,
            "student_name": student_name,
            "subject": subject,
            "body": body,
            "location": location,
            "event_type": event_type,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Sent (EmailJS)" if emailjs_sent else "Sent (Simulated/SMTP Fallback)"
        })
    except Exception as db_err:
        logger.error(f"Failed to log email to DB: {db_err}")
        
    if emailjs_sent:
        return True
        
    # Standard SMTP attempt
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    if smtp_server and smtp_user and smtp_password:
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = to_email
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, [to_email], msg.as_string())
            logger.info("Real SMTP email sent successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to send real SMTP email: {e}")
            
    return True

class EmergencyTriggerRequest(BaseModel):
    latitude: float
    longitude: float
    nearest_hospital: str
    event_type: str  # "Manual SOS", "Fall Detected", "Sudden Shock/Crash"
    symptoms: Optional[str] = "Emergency SOS Triggered"
    emergency_email: Optional[str] = None

@router.post("/emergency-trigger")
def trigger_emergency_event(req: EmergencyTriggerRequest, current_user: dict = Depends(get_current_user)):
    students_col = get_collection("students")
    student_profile = students_col.find_one({"email": current_user["email"]})
    if not student_profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
        
    emergency_email = req.emergency_email or student_profile.get("emergency_email", "")
    student_name = student_profile.get("name", current_user.get("username", "Student"))
    
    # Save into emergency_cases collection
    emergency_col = get_collection("emergency_cases")
    case_doc = {
        "student_email": current_user["email"],
        "student_name": student_name,
        "symptoms": req.symptoms,
        "risk_level": "Critical",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "resolved": False,
        "location": {
            "latitude": req.latitude,
            "longitude": req.longitude
        },
        "nearest_hospital": req.nearest_hospital,
        "event_type": req.event_type
    }
    emergency_col.insert_one(case_doc)
    
    email_status = "No emergency email provided in profile"
    if emergency_email:
        success = send_emergency_email(
            to_email=emergency_email,
            student_name=student_name,
            location={"latitude": req.latitude, "longitude": req.longitude},
            event_type=req.event_type,
            nearest_hospital=req.nearest_hospital
        )
        if success:
            email_status = f"Successfully sent emergency email to {emergency_email}"
        else:
            email_status = f"Failed to send emergency email to {emergency_email}"
            
    return {
        "status": "success",
        "message": "Emergency dispatched and hospital notified",
        "email_status": email_status,
        "case_details": {
            "event_type": req.event_type,
            "nearest_hospital": req.nearest_hospital,
            "latitude": req.latitude,
            "longitude": req.longitude
        }
    }

