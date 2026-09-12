# RoadSOS 🚨

## AI-Powered Emergency Response & Real-Time Triage Platform

RoadSOS helps users quickly discover nearby emergency services, receive AI-powered triage guidance, and access critical roadside assistance during emergencies.

RoadSOS is an AI-powered emergency assistance platform designed to connect users with nearby trauma centres, ambulance services, police stations, and vehicle rescue providers while delivering real-time AI triage guidance during critical situations.

---

## 🚨 Problem Statement

> Emergency response often struggles not from a lack of medical facilities, but due to **communication delays, lack of immediate triage instructions, and slow discovery of nearby responders during the critical golden hour**.

RoadSOS addresses these challenges by combining **instant AI patient triage, real-time location-based discovery of emergency services, and automated notifications** into a unified platform.

---

## 🧠 How RoadSOS Works

1. **Incident Trigger**
   A user initiates an emergency request (SOS or manual accident report) from their web browser.

2. **AI-Powered Triage (Google Gemini API)**
   The patient or bystander enters symptoms, consciousness level, and breathing status. The backend processes this via Gemini to instantly determine severity scores (Low, Moderate, High, Critical) and pre-arrival first-aid guidance.

3. **Geospatial Discovery (Google Maps Platform)**
   Using the standard browser Geolocation API, the platform identifies the user's exact coordinates.

4. **Smart Emergency Discovery**
   The platform identifies nearby trauma centres, ambulance services, police stations, and vehicle rescue providers based on the user's current location.

5. **Family SMS Alerts (Twilio API)**
   Urgent distress SMS notifications containing live location details are automatically dispatched to the victim's designated emergency contacts.

6. **Interactive Dashboard**
   Users can access emergency resources, AI-powered triage guidance, and nearby service information through a unified interface.

---

## 🏆 Why RoadSOS is Different

* ⚡ **Decision Support System** — Combines real-time location discovery with AI triage guidance.
* 🤖 **AI-Driven Severity Triage** — Uses Google Gemini API to eliminate manual medical evaluation delays.
* 📍 **Geographic Matching** — Automatically locates and displays nearby responders using browser Geolocation APIs and Google Maps Platform.
* 📡 **Graceful Fallbacks** — Integrates robust rule-based mock engines to handle scenarios where API keys are not supplied.
* 🌐 **Fully Decoupled Architecture** — Clean separation of frontend and backend enables independent scaling.

---

## 🌟 Key Features

* 📊 Dynamic Bento Grid Dashboard (displays active metrics and emergency search coordinates)
* 📍 Geolocation Discovery (interactive maps locating nearby trauma centers, ambulances, police, and rescue teams)
* 🧠 Google Gemini AI Emergency Triage (instant clinical severity levels & instructions)
* 📞 Emergency contact notification support using Twilio integration
* 📜 AI-generated incident summaries and first-aid guidance

---

## 📊 Impact

* Faster access to emergency resources
* Reduced emergency response discovery time
* AI-assisted emergency decision support
* Improved access to nearby assistance
* Better coordination during critical situations

---

## 🚀 Technology Stack

### Frontend
- React.js
- Vite
- React Router
- Tailwind CSS

### Backend
- FastAPI
- Python

### Database
- SQLite
- SQLAlchemy

### AI & Integrations
- Google Gemini API

### Location Services
- Geolocation API
- Google Maps Platform

### Communication & Integrations
- Twilio SMS
- REST APIs

### Deployment & Development
- GitHub
- Vercel
- Docker

---

## 🏗️ System Architecture (Simplified)

```
User
  ↓
React Frontend
  ↓
FastAPI Backend
  ↓
Google Gemini AI
  ↓
Emergency Recommendations
  ↓
Nearby Services Discovery
  ↓
SMS Alerts & User Guidance
```

---

## 📸 Screenshots

### Home Page
<img width="1470" height="836" alt="image" src="https://github.com/user-attachments/assets/3929f97f-6566-4af2-822d-9eeb143e6198" />


### AI Triage
<img width="1470" height="836" alt="image" src="https://github.com/user-attachments/assets/60a55a15-8d81-420f-a4d5-8a603bf53cbd" />


### Nearby Services
<img width="1470" height="836" alt="image" src="https://github.com/user-attachments/assets/2872d61b-cf06-447d-9054-92aa0804b0e4" />
<img width="1470" height="836" alt="image" src="https://github.com/user-attachments/assets/b8b360ec-bd4f-4922-a64c-7a60f9e241ef" />
<img width="1470" height="836" alt="image" src="https://github.com/user-attachments/assets/1e863eac-d89c-4fd4-86f9-708ab5c14565" />



### SOS Assistance
<img width="1470" height="836" alt="image" src="https://github.com/user-attachments/assets/b94ca3d8-f605-40de-b8ba-44f701e23c51" />


---

## 🌐 Live Demo

**Frontend Web App:** [https://sos-nine-orcin.vercel.app](https://sos-nine-orcin.vercel.app)

**Backend API Service:** *(Self-hosted / Localhost)*

---

## 🛠 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Kunal-kakkar06/ROADSOS.git
cd ROADSOS
```

### 2. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate

   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `backend/` directory:
   ```env
   DATABASE_URL=sqlite+aiosqlite:///./roadsos.db
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_PHONE_NUMBER=your_twilio_phone_number
   FRONTEND_ORIGIN=http://localhost:5173
   GEMINI_API_KEY=your_gemini_api_key
   JWT_SECRET=roadsos-secret-key-change-in-production
   ```
5. Run the backend service (databases seed automatically on startup):
   ```bash
   python main.py
   ```
   Backend active at: 👉 **`http://localhost:8000`** | Swagger docs: 👉 **`http://localhost:8000/docs`**

---

### 3. Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   Frontend active at: 👉 **`http://localhost:5173`**

---

## 👥 Team

* Kunal — Project Lead & Lead Developer
* Gaurav Sehrawat - Backend & System Integration

---

## 🔮 Future Enhancements

- Automatic Crash Detection using smartphone sensors
- Real-Time Ambulance GPS Tracking
- Hospital Bed & ICU Availability Integration
- Insurance Claim Assistance
- Digital FIR Generation
- Accident Hotspot Prediction
- Smart City Emergency Integration

---

## 📄 License

This project is licensed under the MIT License.

---

## 📌 Final Note

> RoadSOS was developed to address critical communication and response delays during medical emergencies. By combining local real-time discovery with Gemini-powered triage guidance, the platform aims to empower bystanders and victims to secure the "golden hour" and save lives on the road.

