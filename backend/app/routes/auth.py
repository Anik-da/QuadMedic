from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from backend.app.database import get_collection
from backend.app.auth import hash_password, verify_password, create_access_token, firebase_initialized, firebase_auth
import random

router = APIRouter(prefix="/auth", tags=["Authentication"])

class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: str # "student", "doctor", "admin"
    # Additional student details if registering as student
    student_id: str = ""
    department: str = ""
    year: str = ""
    blood_group: str = ""
    emergency_email: str = ""

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str

# Simulated OTP storage fallback if DB is not available
_otp_db = {}

def save_otp_to_db(email: str, otp: str):
    try:
        otps_col = get_collection("otps")
        otps_col.update_one(
            {"email": email},
            {"$set": {"otp": otp}},
            upsert=True
        )
    except Exception as e:
        _otp_db[email] = otp

def verify_otp_from_db(email: str, otp: str) -> bool:
    # Always allow 123456 as a master fallback OTP for bulletproof demo ease
    if otp == "123456":
        return True
    try:
        otps_col = get_collection("otps")
        doc = otps_col.find_one({"email": email})
        if doc and doc.get("otp") == otp:
            # Clean up after use
            otps_col.delete_one({"email": email})
            return True
    except Exception:
        pass
    
    # Fallback to local memory db
    stored_otp = _otp_db.get(email)
    if stored_otp and stored_otp == otp:
        _otp_db.pop(email, None)
        return True
        
    return False

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegister):
    users_col = get_collection("users")
    if users_col.find_one({"email": user_data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed = hash_password(user_data.password)
    user_doc = {
        "email": user_data.email,
        "username": user_data.username,
        "hashed_password": hashed,
        "role": user_data.role,
        "uid": f"uid_{random.randint(100000, 999999)}"
    }
    users_col.insert_one(user_doc)
    
    # Initialize profile based on role
    if user_data.role == "student":
        students_col = get_collection("students")
        students_col.insert_one({
            "email": user_data.email,
            "name": user_data.username,
            "student_id": user_data.student_id,
            "department": user_data.department,
            "year": user_data.year,
            "blood_group": user_data.blood_group,
            "emergency_email": user_data.emergency_email,
            "allergies": [],
            "medical_history": [],
            "emergency_contacts": [],
            "chronic_conditions": []
        })
    elif user_data.role == "doctor":
        doctors_col = get_collection("doctors")
        doctors_col.insert_one({
            "email": user_data.email,
            "name": f"Dr. {user_data.username.capitalize()}",
            "specialty": "General Physician",
            "availability": ["Monday", "Wednesday", "Friday"],
            "slots": ["09:00 - 10:00", "10:00 - 11:00", "14:00 - 15:00", "15:00 - 16:00"],
            "queue": []
        })
        
    if firebase_initialized:
        def _bg_create_fb_user():
            try:
                firebase_auth.create_user(
                    uid=user_doc["uid"],
                    email=user_doc["email"],
                    password=user_data.password,
                    display_name=user_doc["username"]
                )
            except Exception as e:
                logger.debug(f"Firebase Auth user creation notice: {e}")
        try:
            import threading
            threading.Thread(target=_bg_create_fb_user, daemon=True).start()
        except Exception:
            pass
            
    return {"message": "Registration successful", "role": user_data.role}

@router.post("/login")
def login_user(credentials: UserLogin):
    users_col = get_collection("users")
    user = users_col.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    token = create_access_token({"sub": user["email"], "role": user["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "username": user["username"],
        "email": user["email"]
    }

@router.post("/otp/send")
def send_otp(req: OTPRequest):
    otp = str(random.randint(100000, 999999))
    save_otp_to_db(req.email, otp)
    print(f"==================================================")
    print(f"[OTP SIMULATION] Verification code for {req.email}: {otp}")
    print(f"==================================================")
    return {"message": "OTP sent successfully (Simulated)", "demo_otp": otp}

@router.post("/otp/verify")
def verify_otp(req: OTPVerify):
    if not verify_otp_from_db(req.email, req.otp):
        raise HTTPException(status_code=400, detail="Invalid OTP code")
    return {"message": "OTP verified successfully"}

@router.post("/forgot-password")
def forgot_password(req: OTPRequest):
    # Triggers simulated email recovery reset
    return {"message": "Password reset email link sent successfully (Simulated)"}

# ============================
# ADMIN USER MANAGEMENT
# ============================
from backend.app.auth import get_current_user

@router.get("/admin/users")
def admin_list_users(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    users_col = get_collection("users")
    users = []
    for u in users_col.find():
        if "_id" in u:
            u["_id"] = str(u["_id"])
        u.pop("hashed_password", None)
        users.append(u)
    return users

@router.delete("/admin/users/{email}")
def admin_delete_user(email: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    users_col = get_collection("users")
    result = users_col.delete_one({"email": email})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    # Also clean up related data
    get_collection("students").delete_many({"email": email})
    get_collection("health_scores").delete_many({"student_email": email})
    get_collection("symptoms").delete_many({"student_email": email})
    get_collection("chat_history").delete_many({"student_email": email})
    get_collection("appointments").delete_many({"student_email": email})
    get_collection("medicine_reminders").delete_many({"student_email": email})
    get_collection("vaccinations").delete_many({"student_email": email})
    
    if firebase_initialized:
        try:
            fb_user = firebase_auth.get_user_by_email(email)
            firebase_auth.delete_user(fb_user.uid)
        except Exception as e:
            print(f"Firebase Auth user deletion warning: {e}")
            
    return {"message": f"User {email} and all related data deleted successfully"}

@router.delete("/admin/users-all")
def admin_delete_all_users(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    users_col = get_collection("users")
    # Delete all non-admin users
    result = users_col.delete_many({"role": {"$ne": "admin"}})
    # Clean up related collections
    for col_name in ["students", "health_scores", "symptoms", "chat_history", 
                     "appointments", "medicine_reminders", "vaccinations",
                     "clinical_notes", "emergency_cases", "medical_reports"]:
        get_collection(col_name).delete_many({})
        
    if firebase_initialized:
        try:
            page = firebase_auth.list_users()
            while page:
                for fb_user in page.users:
                    if fb_user.email != "admin@quadmedic.com" and fb_user.email != current_user.get("email"):
                        try:
                            firebase_auth.delete_user(fb_user.uid)
                        except Exception:
                            pass
                page = page.get_next_page()
        except Exception as e:
            print(f"Firebase Auth bulk user deletion warning: {e}")
            
    return {"message": f"Deleted {result.deleted_count} user accounts and all related data"}
