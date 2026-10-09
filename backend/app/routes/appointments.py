from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from backend.app.database import get_collection
from backend.app.auth import get_current_user
import random

router = APIRouter(prefix="/appointments", tags=["Appointments Queue"])

class AppointmentBooking(BaseModel):
    doctor_email: str
    date: str # "YYYY-MM-DD"
    slot: str # "09:00 - 10:00"
    reason: str

@router.get("/doctors")
def get_doctors_list():
    docs_col = get_collection("doctors")
    doctors = docs_col.find()
    list_docs = []
    for d in doctors:
        if "_id" in d:
            d["_id"] = str(d["_id"])
        list_docs.append(d)
        
    # Auto-seed doctors if empty to keep demo fully functional
    if not list_docs:
        docs = [
            {"email": "smith@quadmedic.edu", "name": "Dr. Sarah Smith", "specialty": "Cardiology & General Medicine", "availability": ["Monday", "Tuesday", "Wednesday"], "slots": ["09:00 - 10:00", "10:00 - 11:00", "14:00 - 15:00"], "queue": []},
            {"email": "davis@quadmedic.edu", "name": "Dr. Alan Davis", "specialty": "Pediatrics & General Care", "availability": ["Wednesday", "Thursday", "Friday"], "slots": ["10:00 - 11:00", "11:00 - 12:00", "15:00 - 16:00"], "queue": []},
            {"email": "jones@quadmedic.edu", "name": "Dr. Emily Jones", "specialty": "Mental Wellness & Psychology", "availability": ["Monday", "Thursday"], "slots": ["09:00 - 10:00", "11:00 - 12:00", "14:00 - 15:00"], "queue": []}
        ]
        for d in docs:
            docs_col.insert_one(d)
            if "_id" in d:
                d["_id"] = str(d["_id"])
            list_docs.append(d)
            
    return list_docs

@router.post("/book")
def book_appointment(booking: AppointmentBooking, current_user: dict = Depends(get_current_user)):
    appointments_col = get_collection("appointments")
    
    # Calculate queue number based on existing bookings for this doctor on this day
    existing_count = appointments_col.count_documents({
        "doctor_email": booking.doctor_email,
        "date": booking.date,
        "status": "booked"
    })
    queue_number = existing_count + 1
    
    appt_doc = booking.model_dump()
    appt_doc["student_email"] = current_user["email"]
    appt_doc["student_name"] = current_user.get("username", "Student")
    appt_doc["queue_number"] = queue_number
    appt_doc["status"] = "booked" # booked, completed, cancelled
    appt_doc["id"] = f"apt_{random.randint(10000, 99999)}"
    
    appointments_col.insert_one(appt_doc)
    return {
        "message": "Appointment booked successfully",
        "queue_number": queue_number,
        "appointment_id": appt_doc["id"]
    }

@router.get("/my-bookings")
def get_my_bookings(current_user: dict = Depends(get_current_user)):
    appointments_col = get_collection("appointments")
    # For students
    if current_user["role"] == "student":
        bookings = appointments_col.find({"student_email": current_user["email"]})
    # For doctors
    elif current_user["role"] == "doctor":
        bookings = appointments_col.find({"doctor_email": current_user["email"]})
    else: # Admin gets all
        bookings = appointments_col.find()
        
    list_book = []
    for b in bookings:
        if "_id" in b:
            b["_id"] = str(b["_id"])
        list_book.append(b)
    return list_book

@router.post("/cancel/{appointment_id}")
def cancel_appointment(appointment_id: str, current_user: dict = Depends(get_current_user)):
    appointments_col = get_collection("appointments")
    appt = appointments_col.find_one({"id": appointment_id})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    appointments_col.update_one({"id": appointment_id}, {"$set": {"status": "cancelled"}})
    return {"message": "Appointment cancelled successfully"}
