# Apply DNS-over-HTTPS (DoH) monkeypatch before any other imports
import backend.app.doh_resolver

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routes import auth, students, appointments, ai_services, analytics

app = FastAPI(
    title="QuadMedic API Gateway",
    description="FastAPI Backend for QuadMedic - AI-Powered Smart Healthcare Ecosystem",
    version="1.0.0"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(students.router)
app.include_router(appointments.router)
app.include_router(ai_services.router)
app.include_router(analytics.router)

@app.get("/")
def read_root():
    return {
        "status": "Online",
        "service": "QuadMedic Healthcare Core Server",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth",
            "students": "/students",
            "appointments": "/appointments",
            "ai": "/ai",
            "analytics": "/analytics"
        }
    }
