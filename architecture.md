# QuadMedic - System Architecture & Database Design

This document details the software architecture, database collections schema (ER Diagram), and decision-making flowcharts for the QuadMedic smart campus healthcare ecosystem.

---

## 1. System Architecture Diagram

The system follows a split client-server design where the **PyQt6 Desktop Client** acts as a visually rich native user interface and communicates via standard HTTP REST requests to the **FastAPI Backend Core Server**.

```mermaid
graph TD
    %% Frontend Client
    subgraph PyQt6_Client["PyQt6 Desktop Application"]
        MainLauncher["App Launcher (run.py)"]
        APIClient["API Connection Gateway (api_client.py)"]
        GlassUI["Frosted Liquid Glass Frame"]
        StudentDash["Student Workspace Widget"]
        DoctorDash["Physician Work Station"]
        AdminDash["Analytics Console (Matplotlib)"]
        
        MainLauncher --> GlassUI
        GlassUI --> StudentDash
        GlassUI --> DoctorDash
        GlassUI --> AdminDash
        StudentDash --> APIClient
        DoctorDash --> APIClient
        AdminDash --> APIClient
    end

    %% Backend Server
    subgraph FastAPI_Server["FastAPI Backend Server (main.py)"]
        RoutesAuth["Auth & 2FA Router (auth.py)"]
        RoutesStud["Students Info Router (students.py)"]
        RoutesAppt["Appointments Scheduler (appointments.py)"]
        RoutesAI["AI Copilot Gateway (ai_services.py)"]
        RoutesAnal["Metrics & PDF Export (analytics.py)"]
        
        APIClient -->|HTTP GET/POST/PUT| RoutesAuth
        APIClient -->|HTTP GET/PUT| RoutesStud
        APIClient -->|HTTP GET/POST| RoutesAppt
        APIClient -->|HTTP POST/Multipart| RoutesAI
        APIClient -->|HTTP GET/PDF| RoutesAnal
    end

    %% AI Models Inference Engine
    subgraph AI_Engine["Hugging Face Local / Fallback Engines"]
        SymptomModel["BART-large-mnli (Symptom Classifier)"]
        ChatbotModel["DialoGPT-medium (Conversation)"]
        RiskModel["MiniLM-L6-v2 (Embedding Similarity)"]
        WellnessModel["distilroberta-base (Emotion)"]
        OCRModel["TrOCR + Flan-T5 (OCR summarization)"]
        VoiceModel["Whisper + SpeechT5 (STT/TTS)"]
        
        RoutesAI --> SymptomModel
        RoutesAI --> ChatbotModel
        RoutesAI --> RiskModel
        RoutesAI --> WellnessModel
        RoutesAI --> OCRModel
        RoutesAI --> VoiceModel
    end

    %% Databases & Storage
    subgraph Storage_Layer["Database & Cloud Services"]
        MongoDB[(MongoDB Atlas)]
        Firebase[(Firebase Authentication & Storage)]
        
        RoutesAuth -->|CRUD logs| MongoDB
        RoutesStud -->|Read/Write Profile| MongoDB
        RoutesAppt -->|Queue States| MongoDB
        RoutesAnal -->|Extract analytics| MongoDB
        
        RoutesAuth -->|Verify ID Tokens| Firebase
        RoutesAI -->|Mock Upload Report PDFs| Firebase
    end
```

---

## 2. Entity-Relationship (ER) Diagram (MongoDB Schema)

Although MongoDB is schemaless, QuadMedic enforces clean document models. Relationships are managed via matching fields (e.g. `student_email` or `doctor_email`).

```mermaid
erDiagram
    USERS {
        string _id PK
        string email
        string username
        string hashed_password
        string role "student | doctor | admin"
        string uid
    }
    STUDENTS {
        string _id PK
        string email FK "References USERS"
        string name
        string student_id
        string department
        string year
        string blood_group
        array allergies
        array chronic_conditions
        array emergency_contacts
    }
    DOCTORS {
        string _id PK
        string email FK "References USERS"
        string name
        string specialty
        array availability
        array slots
        array queue
    }
    APPOINTMENTS {
        string _id PK
        string id
        string student_email FK "References STUDENTS"
        string student_name
        string doctor_email FK "References DOCTORS"
        string date
        string slot
        string reason
        int queue_number
        string status "booked | completed | cancelled"
    }
    MEDICINE_REMINDERS {
        string _id PK
        string student_email FK "References STUDENTS"
        string medicine_name
        string dosage
        string frequency
        array times
        boolean is_active
    }
    VACCINATIONS {
        string _id PK
        string student_email FK "References STUDENTS"
        string vaccine_name
        int dose_number
        string date_administered
        string administered_by
    }
    EMERGENCY_CASES {
        string _id PK
        string student_email FK "References STUDENTS"
        string student_name
        string symptoms
        string risk_level
        string timestamp
        boolean resolved
    }
    HEALTH_SCORES {
        string _id PK
        string student_email FK "References STUDENTS"
        int age
        double bmi
        double sleep_hours
        double water_intake_l
        string activity_level
        string symptoms
        double health_score
        string risk_category
        string timestamp
    }

    USERS ||--o| STUDENTS : "defines student profile"
    USERS ||--o| DOCTORS : "defines doctor profile"
    STUDENTS ||--o{ APPOINTMENTS : "books"
    DOCTORS ||--o{ APPOINTMENTS : "attends"
    STUDENTS ||--o{ MEDICINE_REMINDERS : "schedules"
    STUDENTS ||--o{ VACCINATIONS : "logs"
    STUDENTS ||--o{ EMERGENCY_CASES : "triggers"
    STUDENTS ||--o{ HEALTH_SCORES : "calculates"
```

---

## 3. Symptom Diagnosis & Emergency Triage Flowchart

This flowchart outlines the triage process for symptom classification.

```mermaid
flowchart TD
    Start([Student enters symptoms]) --> InputText[Symptoms Text Input]
    InputText --> MatchEmergency{Contains Emergency Keywords?\n- chest pain\n- breathing difficulty\n- loss of consciousness\n- seizures\n- high fever}
    
    MatchEmergency -->|Yes| TriggerRedAlert[1. Force Risk Category: CRITICAL\n2. Log Case in EMERGENCY_CASES\n3. Display Fullscreen Red Alert Window]
    TriggerRedAlert --> ActionAlert[Show Nearest Hospitals, Ambulance Hotline, and Call Trigger]
    
    MatchEmergency -->|No| LoadModel{USE_REAL_AI_MODELS = True?}
    
    LoadModel -->|Yes| RunModel[Process text using facebook/bart-large-mnli Zero-Shot pipeline]
    RunModel --> CheckRisk{Predicted Risk Category?}
    CheckRisk -->|Critical / High| TriggerRedAlert
    CheckRisk -->|Medium / Low| DisplayDiag[Show Diagnosis, Confidence Score, and Recommended Actions]
    
    LoadModel -->|No| RunHeuristics[Analyze via Keyword Lookup Database]
    RunHeuristics --> DisplayDiag
    
    DisplayDiag --> End([Triage Finished])
    ActionAlert --> End
```
