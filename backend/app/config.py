import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "quadmedic")

# Google Gemini API Key (primary AI engine replacing Hugging Face/OpenRouter)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")
os.environ["HF_TOKEN"] = HF_TOKEN

# Firebase Config (provided in screenshot/specification)
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")
FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN", "quad-medic.firebaseapp.com")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "quad-medic")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "quad-medic.firebasestorage.app")
FIREBASE_MESSAGING_SENDER_ID = os.getenv("FIREBASE_MESSAGING_SENDER_ID", "")
FIREBASE_APP_ID = os.getenv("FIREBASE_APP_ID", "")
FIREBASE_DATABASE_URL = os.getenv(
    "FIREBASE_DATABASE_URL", 
    f"https://{FIREBASE_PROJECT_ID}-default-rtdb.firebaseio.com"
)
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "realtime_database")

# EmailJS Configuration
EMAILJS_SERVICE_ID = os.getenv("EMAILJS_SERVICE_ID", "")
EMAILJS_TEMPLATE_ID = os.getenv("EMAILJS_TEMPLATE_ID", "")
EMAILJS_USER_ID = os.getenv("EMAILJS_USER_ID", "")
EMAILJS_ACCESS_TOKEN = os.getenv("EMAILJS_ACCESS_TOKEN", "")

# Secret key for JWT session verification fallback
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-quad-medic-key-2026")
JWT_ALGORITHM = "HS256"

# AI Inference Settings
# Set this to True to attempt loading full Hugging Face models.
# If False, the backend uses highly optimized and realistic rule-based/mock pipelines.
USE_REAL_AI_MODELS = os.getenv("USE_REAL_AI_MODELS", "False").lower() in ("true", "1", "yes")

# Root directory path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
