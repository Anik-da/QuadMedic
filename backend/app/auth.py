import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

from backend.app.config import FIREBASE_PROJECT_ID, FIREBASE_DATABASE_URL, JWT_SECRET, JWT_ALGORITHM
from backend.app.database import get_collection

logger = logging.getLogger("quadmedic.auth")

# Password hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# HTTP Bearer security scheme
security = HTTPBearer()

# Initialize Firebase Admin if configuration/certificates are present.
# Otherwise, we gracefully log the fallback to local auth.
firebase_initialized = False
try:
    if not firebase_admin._apps:
        options = {
            'projectId': FIREBASE_PROJECT_ID,
            'databaseURL': FIREBASE_DATABASE_URL
        }
        firebase_admin.initialize_app(options=options)
    firebase_initialized = True
    logger.info("Firebase Admin initialized successfully.")
except Exception as e:
    logger.warning(f"Firebase Admin not initialized (using local credentials fallback): {e}")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Fast local JWT validation first
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email:
            users_col = get_collection("users")
            user = users_col.find_one({"email": email})
            if user:
                return user
    except Exception:
        pass

    # Try Firebase verification if local token decoding didn't succeed
    if firebase_initialized:
        try:
            decoded_token = firebase_auth.verify_id_token(token)
            uid = decoded_token.get("uid")
            email = decoded_token.get("email")
            
            # Look up user in RTDB collection
            users_col = get_collection("users")
            user = users_col.find_one({"email": email})
            if not user:
                # Auto-register in DB if verified via Firebase
                user = {
                    "email": email,
                    "uid": uid,
                    "role": "student", # Default role
                    "username": email.split("@")[0],
                }
                users_col.insert_one(user)
            return user
        except Exception:
            pass

    raise credentials_exception

def require_role(allowed_roles: list[str]):
    def dependency(current_user: dict = Depends(get_current_user)):
        role = current_user.get("role", "student")
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        return current_user
    return dependency
