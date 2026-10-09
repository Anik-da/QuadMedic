from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from backend.app.database import get_collection
from backend.app.auth import get_current_user

router = APIRouter(prefix="/students", tags=["Student Profile & History"])

class StudentProfileUpdate(BaseModel):
    name: Optional[str] = ""
    student_id: Optional[str] = ""
    department: Optional[str] = ""
    year: Optional[str] = ""
    blood_group: Optional[str] = ""
    allergies: Optional[List[str]] = []
    chronic_conditions: Optional[List[str]] = []
    emergency_contacts: Optional[List[dict]] = []  # [{"name": "Mom", "phone": "12345"}, ...]
    emergency_email: Optional[str] = None

class VaccinationRecord(BaseModel):
    vaccine_name: str # "COVID-19", "Hepatitis B", "Tetanus", "MMR"
    dose_number: int
    date_administered: str
    expiry_date: Optional[str] = None
    administered_by: str

class MedicineReminder(BaseModel):
    medicine_name: str
    dosage: str # "1 pill", "5ml"
    frequency: str # "Daily", "Twice Daily"
    times: List[str] # ["08:00", "20:00"]
    is_active: bool = True

@router.get("/profile")
def get_student_profile(current_user: dict = Depends(get_current_user)):
    students_col = get_collection("students")
    profile = students_col.find_one({"email": current_user["email"]})
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    # Clean up MongoDB _id field for JSON serialization
    if "_id" in profile:
        profile["_id"] = str(profile["_id"])
    return profile

@router.put("/profile")
def update_student_profile(profile_data: StudentProfileUpdate, current_user: dict = Depends(get_current_user)):
    students_col = get_collection("students")
    res = students_col.update_one(
        {"email": current_user["email"]},
        {"$set": profile_data.model_dump()},
        upsert=True
    )
    return {"message": "Profile updated successfully"}

@router.get("/vaccinations")
def get_vaccination_records(current_user: dict = Depends(get_current_user)):
    vacc_col = get_collection("vaccinations")
    records = vacc_col.find({"student_email": current_user["email"]})
    # Convert list
    list_rec = []
    for r in records:
        if "_id" in r:
            r["_id"] = str(r["_id"])
        list_rec.append(r)
    return list_rec

@router.post("/vaccinations")
def add_vaccination_record(record: VaccinationRecord, current_user: dict = Depends(get_current_user)):
    vacc_col = get_collection("vaccinations")
    rec_doc = record.model_dump()
    rec_doc["student_email"] = current_user["email"]
    vacc_col.insert_one(rec_doc)
    return {"message": "Vaccination record logged successfully"}

@router.get("/reminders")
def get_medicine_reminders(current_user: dict = Depends(get_current_user)):
    rem_col = get_collection("medicine_reminders")
    reminders = rem_col.find({"student_email": current_user["email"]})
    list_rem = []
    for r in reminders:
        if "_id" in r:
            r["_id"] = str(r["_id"])
        list_rem.append(r)
    return list_rem

@router.post("/reminders")
def create_medicine_reminder(reminder: MedicineReminder, current_user: dict = Depends(get_current_user)):
    rem_col = get_collection("medicine_reminders")
    rem_doc = reminder.model_dump()
    rem_doc["student_email"] = current_user["email"]
    rem_col.insert_one(rem_doc)
    return {"message": "Medicine reminder scheduled successfully"}

@router.put("/reminders/{reminder_id}/toggle")
def toggle_reminder(reminder_id: str, current_user: dict = Depends(get_current_user)):
    rem_col = get_collection("medicine_reminders")
    # Use fallback compatible update
    reminder = rem_col.find_one({"_id": reminder_id})
    if not reminder:
        # Check string vs int ID
        reminder = rem_col.find_one({"_id": str(reminder_id)})
        
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
        
    new_status = not reminder.get("is_active", True)
    rem_col.update_one({"_id": reminder["_id"]}, {"$set": {"is_active": new_status}})
    return {"message": f"Reminder status updated to {new_status}"}

class ClinicalNote(BaseModel):
    patient_email: str
    diagnosis: str
    prescription: str

@router.post("/clinical-notes")
def create_clinical_note(note: ClinicalNote, current_user: dict = Depends(get_current_user)):
    import datetime
    notes_col = get_collection("clinical_notes")
    note_doc = note.model_dump()
    note_doc["doctor_email"] = current_user["email"]
    note_doc["doctor_name"] = current_user.get("username", "Doctor")
    note_doc["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    notes_col.insert_one(note_doc)
    return {"message": "Clinical note saved successfully"}
