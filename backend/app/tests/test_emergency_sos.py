import unittest
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_collection
from backend.app.auth import hash_password

class TestEmergencySOS(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.users_col = get_collection("users")
        self.students_col = get_collection("students")
        self.emergency_col = get_collection("emergency_cases")
        self.emails_col = get_collection("emergency_emails")
        
        # Clean up database records
        self.test_email = "tester_student@example.com"
        self.users_col.delete_one({"email": self.test_email})
        self.students_col.delete_one({"email": self.test_email})
        self.emergency_col.delete_many({"student_email": self.test_email})
        self.emails_col.delete_many({"recipient": "guardian_tester@example.com"})

    def tearDown(self):
        # Clean up database records
        self.users_col.delete_one({"email": self.test_email})
        self.students_col.delete_one({"email": self.test_email})
        self.emergency_col.delete_many({"student_email": self.test_email})
        self.emails_col.delete_many({"recipient": "guardian_tester@example.com"})

    def test_full_emergency_flow(self):
        # 1. Register a student with emergency email
        reg_payload = {
            "email": self.test_email,
            "username": "Test Student",
            "password": "securepassword123",
            "role": "student",
            "student_id": "STD-TEST-001",
            "department": "Biomedical Engineering",
            "year": "4th Year",
            "blood_group": "A-positive",
            "emergency_email": "guardian_tester@example.com"
        }
        reg_resp = self.client.post("/auth/register", json=reg_payload)
        self.assertEqual(reg_resp.status_code, 201)
        
        # Verify student document has emergency_email
        student_doc = self.students_col.find_one({"email": self.test_email})
        self.assertIsNotNone(student_doc)
        self.assertEqual(student_doc.get("emergency_email"), "guardian_tester@example.com")
        
        # 2. Login to obtain JWT token
        login_resp = self.client.post("/auth/login", json={
            "email": self.test_email,
            "password": "securepassword123"
        })
        self.assertEqual(login_resp.status_code, 200)
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Fetch profile and verify emergency_email is returned
        profile_resp = self.client.get("/students/profile", headers=headers)
        self.assertEqual(profile_resp.status_code, 200)
        self.assertEqual(profile_resp.json().get("emergency_email"), "guardian_tester@example.com")
        
        # 4. Trigger emergency SOS event via API
        sos_payload = {
            "latitude": 37.7850,
            "longitude": -122.4300,
            "nearest_hospital": "Campus Emergency Clinic",
            "event_type": "Sudden Shock/Crash Detected (Accelerometer)",
            "symptoms": "Automated Crash Sensor Triggered"
        }
        sos_resp = self.client.post("/ai/emergency-trigger", json=sos_payload, headers=headers)
        self.assertEqual(sos_resp.status_code, 200)
        
        data = sos_resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("Successfully sent emergency email", data["email_status"])
        
        # 5. Verify database records
        # Emergency case saved
        case_doc = self.emergency_col.find_one({"student_email": self.test_email})
        self.assertIsNotNone(case_doc)
        self.assertEqual(case_doc.get("nearest_hospital"), "Campus Emergency Clinic")
        self.assertEqual(case_doc.get("event_type"), "Sudden Shock/Crash Detected (Accelerometer)")
        
        # Emergency email audit logged
        email_doc = self.emails_col.find_one({"recipient": "guardian_tester@example.com"})
        self.assertIsNotNone(email_doc)
        self.assertEqual(email_doc.get("student_name"), "Test Student")
        self.assertIn("Google Maps Link", email_doc.get("body"))

if __name__ == "__main__":
    unittest.main()
