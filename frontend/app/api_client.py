import requests
import os
import logging
from typing import Optional, dict, List

logger = logging.getLogger("quadmedic.frontend.api")

class QuadMedicAPIClient:
    def __init__(self, base_url: str = "https://quad-medic-backend-134641034875.us-central1.run.app"):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.role: Optional[str] = None
        self.username: Optional[str] = None
        self.email: Optional[str] = None

    def set_token(self, token: str, role: str, username: str, email: str):
        self.token = token
        self.role = role
        self.username = username
        self.email = email

    def logout(self):
        self.token = None
        self.role = None
        self.username = None
        self.email = None

    def _get_headers(self, is_multipart=False) -> dict:
        headers = {}
        if not is_multipart:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def register(self, email: str, username: str, password: str, role: str, student_id: str = "", dept: str = "", year: str = "", blood: str = "") -> dict:
        url = f"{self.base_url}/auth/register"
        data = {
            "email": email,
            "username": username,
            "password": password,
            "role": role,
            "student_id": student_id,
            "department": dept,
            "year": year,
            "blood_group": blood
        }
        res = requests.post(url, json=data)
        res.raise_for_status()
        return res.json()

    def login(self, email: str, password: str) -> dict:
        url = f"{self.base_url}/auth/login"
        res = requests.post(url, json={"email": email, "password": password})
        res.raise_for_status()
        data = res.json()
        self.set_token(
            token=data["access_token"],
            role=data["role"],
            username=data["username"],
            email=data["email"]
        )
        return data

    def send_otp(self, email: str) -> dict:
        url = f"{self.base_url}/auth/otp/send"
        res = requests.post(url, json={"email": email})
        res.raise_for_status()
        return res.json()

    def verify_otp(self, email: str, otp: str) -> dict:
        url = f"{self.base_url}/auth/otp/verify"
        res = requests.post(url, json={"email": email, "otp": otp})
        res.raise_for_status()
        return res.json()

    # Student Profile
    def get_profile(self) -> dict:
        url = f"{self.base_url}/students/profile"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def update_profile(self, name: str, student_id: str, dept: str, year: str, blood: str, allergies: List[str], conditions: List[str], contacts: List[dict]) -> dict:
        url = f"{self.base_url}/students/profile"
        data = {
            "name": name,
            "student_id": student_id,
            "department": dept,
            "year": year,
            "blood_group": blood,
            "allergies": allergies,
            "chronic_conditions": conditions,
            "emergency_contacts": contacts
        }
        res = requests.put(url, json=data, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    # Vaccinations
    def get_vaccinations(self) -> List[dict]:
        url = f"{self.base_url}/students/vaccinations"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def add_vaccination(self, name: str, dose: int, date: str, expiry: Optional[str], admin_by: str) -> dict:
        url = f"{self.base_url}/students/vaccinations"
        data = {
            "vaccine_name": name,
            "dose_number": dose,
            "date_administered": date,
            "expiry_date": expiry,
            "administered_by": admin_by
        }
        res = requests.post(url, json=data, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    # Reminders
    def get_reminders(self) -> List[dict]:
        url = f"{self.base_url}/students/reminders"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def add_reminder(self, name: str, dosage: str, freq: str, times: List[str]) -> dict:
        url = f"{self.base_url}/students/reminders"
        data = {
            "medicine_name": name,
            "dosage": dosage,
            "frequency": freq,
            "times": times,
            "is_active": True
        }
        res = requests.post(url, json=data, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def toggle_reminder(self, reminder_id: str) -> dict:
        url = f"{self.base_url}/students/reminders/{reminder_id}/toggle"
        res = requests.put(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    # Appointments
    def get_doctors(self) -> List[dict]:
        url = f"{self.base_url}/appointments/doctors"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def book_appointment(self, doctor_email: str, date: str, slot: str, reason: str) -> dict:
        url = f"{self.base_url}/appointments/book"
        data = {
            "doctor_email": doctor_email,
            "date": date,
            "slot": slot,
            "reason": reason
        }
        res = requests.post(url, json=data, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def get_my_bookings(self) -> List[dict]:
        url = f"{self.base_url}/appointments/my-bookings"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def cancel_appointment(self, appt_id: str) -> dict:
        url = f"{self.base_url}/appointments/cancel/{appt_id}"
        res = requests.post(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    # AI operations
    def analyze_symptoms(self, symptoms: str) -> dict:
        url = f"{self.base_url}/ai/analyze-symptoms"
        res = requests.post(url, json={"symptoms": symptoms}, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def send_chat_message(self, message: str, session_id: Optional[str] = None) -> dict:
        url = f"{self.base_url}/ai/chat"
        res = requests.post(url, json={"message": message, "session_id": session_id}, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def predict_health_risk(self, age: int, weight: float, height: float, sleep: float, water: float, activity: str, symptoms: str) -> dict:
        url = f"{self.base_url}/ai/risk-predict"
        data = {
            "age": age,
            "weight_kg": weight,
            "height_cm": height,
            "sleep_hours": sleep,
            "water_intake_l": water,
            "activity_level": activity,
            "symptoms": symptoms
        }
        res = requests.post(url, json=data, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def check_emotion(self, text: str) -> dict:
        url = f"{self.base_url}/ai/emotion-wellness"
        res = requests.post(url, json={"text": text}, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def get_health_insights(self, sleep: float, water: float, activity: str, symptoms: str, emotion: str) -> dict:
        url = f"{self.base_url}/ai/health-insights"
        data = {
            "sleep_hours": sleep,
            "water_intake_l": water,
            "activity_level": activity,
            "symptoms": symptoms,
            "emotion": emotion
        }
        res = requests.post(url, json=data, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def upload_medical_report(self, file_path: str) -> dict:
        url = f"{self.base_url}/ai/document-analyze"
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, "image/png")}
            res = requests.post(url, files=files, headers=self._get_headers(is_multipart=True))
        res.raise_for_status()
        return res.json()

    def speech_to_text(self, wav_path: str) -> str:
        url = f"{self.base_url}/ai/speech-to-text"
        with open(wav_path, "rb") as f:
            files = {"file": ("audio.wav", f, "audio/wav")}
            res = requests.post(url, files=files, headers=self._get_headers(is_multipart=True))
        res.raise_for_status()
        return res.json().get("transcript", "")

    def text_to_speech(self, text: str, output_path: str) -> bool:
        url = f"{self.base_url}/ai/text-to-speech"
        res = requests.post(url, json={"text": text}, headers=self._get_headers())
        if res.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(res.content)
            return True
        return False

    def search_library(self, query: str) -> List[dict]:
        url = f"{self.base_url}/ai/knowledge-search"
        res = requests.get(url, params={"query": query}, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    # Campus Analytics (Admin dashboard)
    def get_analytics(self) -> dict:
        url = f"{self.base_url}/analytics/campus-dashboard"
        res = requests.get(url, headers=self._get_headers())
        res.raise_for_status()
        return res.json()

    def download_report_pdf(self, output_path: str) -> bool:
        url = f"{self.base_url}/analytics/report/pdf"
        res = requests.get(url, headers=self._get_headers())
        if res.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(res.content)
            return True
        return False
