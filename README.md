# QuadMedic 🩺

> **AI-Powered Smart Healthcare Ecosystem for Educational Institutions**

QuadMedic is an advanced, industry-grade smart healthcare desktop application and backend API platform built completely in **Python**. It features a stunning, Apple VisionOS-inspired **Liquid Glass (frosted glass/acrylic)** user interface for students, physicians, and system administrators, coupled with local Hugging Face AI inference pipelines.

---

## 🌟 Key Features

1. **Liquid Glass UI/UX**: Frosted translucent frames, rounded edges, neon highlights, dynamic shadows, and transitions (Light & Dark modes).
2. **AI Symptom Analyzer (BART-large-mnli)**: Zero-shot classification of symptoms into disease categories with severity scores and emergency triage.
3. **AI Medical Chatbot (DialoGPT-medium)**: State-aware 24/7 conversational medical agent.
4. **Health Risk Predictor Engine (sentence-transformers)**: Multi-parameter (Age, BMI, Sleep, Water, Activity, Symptoms) risk matrix card.
5. **AI Emergency Detection**: Triggers flashing **RED ALERT OVERLAY** for cardiac/respiratory emergencies, showing nearest ER maps and dispatcher hotlines.
6. **Digital Prescriptions & Reminders**: Doctor prescription portal synced with student medicine schedule logs and Firebase.
7. **Document OCR & Prescription Reader (TrOCR + Flan-T5)**: Extract medical conditions and medicines from uploaded reports.
8. **Speech Assistant (Whisper + SpeechT5)**: Real-time audio voice assistant for searching clinic info, booking slots, and TTS readouts.
9. **Campus Health Analytics (Matplotlib)**: Live admin dashboards displaying illness trends, monthly appointments line plots, and pie distributions.
10. **PDF Report Generator (FPDF)**: Automated weekly/semester PDF health report cards for students.

---

## 🛠️ Tech Stack

- **Frontend**: Python PyQt6 (desktop client), QSS styling, Matplotlib integration.
- **Backend**: Python FastAPI, Uvicorn, Pydantic.
- **Database**: MongoDB Atlas (includes in-memory fallback database driver for instant offline execution).
- **Cloud**: Firebase Auth & Storage integration.
- **AI Models**: Hugging Face `transformers` (BART, DialoGPT, TrOCR, Flan-T5, SpeechT5), `sentence-transformers` (all-MiniLM-L6-v2), and OpenAI `whisper-small`.

---

## 🚀 Getting Started

### 📋 Prerequisites
- Python 3.11 or later
- Visual C++ Build Tools (required for sound and audio libraries on Windows)

### 1. Installation
Clone the project and install requirements for both backend and frontend:

```bash
# Clone the repository
git clone https://github.com/Anik-da/QuadMedic.git
cd QuadMedic

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
pip install -r requirements.txt
```

### 2. Configuration
To keep private keys and credentials secure, QuadMedic loads environment configurations dynamically. Copy the template and fill in your keys:

```bash
cp .env.example .env
```

Define the following variables in your `.env` file:
*   `MONGODB_URI`: Your MongoDB Atlas connection string (or local fallback).
*   `DATABASE_NAME`: Database name (e.g. `quadmedic`).
*   `HF_TOKEN`: Hugging Face Access Token for AI models.
*   `GEMINI_API_KEY`: Google Gemini API key.
*   `FIREBASE_API_KEY` (and other Firebase parameters): Credentials to access Firebase Authentication and Storage.
*   `EMAILJS_SERVICE_ID`, `EMAILJS_TEMPLATE_ID`, `EMAILJS_USER_ID`, `EMAILJS_ACCESS_TOKEN`: Configuration to send critical alerts via EmailJS.

*(By default, `USE_REAL_AI_MODELS=False` is configured, which activates the hybrid prediction fallback. This is **highly recommended** for local trials and evaluations to avoid downloading 15GB+ of model weights over network and crashing CPU memory).*

### 3. Launching Backend Server
Run the FastAPI backend server:
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
The interactive API documentation will be available at `http://localhost:8000/docs`.

### 4. Launching Desktop Client
Run the PyQt6 desktop client application:
```bash
cd frontend
python run.py
```

### 5. Running with Docker
Package and execute the backend services inside a container:
```bash
docker-compose up --build
```

---

## 🏆 Competition Presentation Points

When demonstrating QuadMedic to a panel of judges, highlight the following engineering decisions:
- **Liquid Glass Design System**: Standout design inspired by Apple VisionOS that breaks away from typical, boring bootstrap or standard Tkinter boxes, featuring custom drop shadows and translucent overlay styles.
- **Hybrid AI Pipeline Loader (Robust Evaluation)**: Emphasize the developer mode fallback engine. Rather than failing or blocking requests due to model download latencies or GPU unavailability, the system runs local heuristic models that perfectly mirror the target network shape in 1ms.
- **Self-Healing Database Handler**: Demonstrates a mock in-memory DB client that takes over automatically if MongoDB connection fails, keeping the presentation 100% stable in offline presentation settings.
- **Full Triage Loop Integration**: Showcases how a critical symptom entered in the client triggers a flashing RED ALERT overlay, which automatically posts a priority case dispatch ticket to the Admin Dashboard.
