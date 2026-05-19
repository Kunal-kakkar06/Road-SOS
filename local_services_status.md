# RoadSOS Local Service Dashboard

Your local environment for the **RoadSOS Emergency Response** application is now fully configured and actively running! Both backend and frontend services have been started in the background.

---

## 🚀 Running Services

| Service | Local Address | Port | Status | Command Run |
| :--- | :--- | :--- | :--- | :--- |
| **FastAPI Backend** | [http://localhost:8000](http://localhost:8000) | `8000` | 🟢 **Active** | `.\venv\Scripts\python.exe main.py` |
| **Frontend Web App** | [http://localhost:5500/index.html](http://localhost:5500/index.html) | `5500` | 🟢 **Active** | `.\backend\venv\Scripts\python.exe -m http.server 5500` |
| **MySQL Database** | `localhost` | `3306` | 🟢 **Connected** | *Active Windows System Service* |

---

## 🛠️ How to Access & Test

### 1. Frontend Interface
Open your browser and navigate to:
👉 **[http://localhost:5500/index.html](http://localhost:5500/index.html)**

You will see the premium, responsive Bento-style **RoadSOS Landing Page** where you can:
- **Test AI Triage**: Fill out triage diagnostics.
- **Trigger Emergency SOS**: Test instant ambulance dispatches connecting in real-time to your FastAPI backend and pulling seeded driver/provider details from your MySQL database.
- **View Blackspot Map**: Interactively view high-risk accident zones nearby.

### 2. Backend API Documentation
You can inspect the FastAPI automatic docs to interact with and test individual endpoints:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 📊 Database Status
- **Connected Database**: `roadsos` on MySQL (`localhost:3306`)
- **Seeding**: Already verified and fully seeded with **10 verified hospital providers** and **20 active ambulances** in the Bengaluru region.

---

> [!TIP]
> Both services are running asynchronously in the background. If you want to stop them later, you can stop the terminals or run standard command termination commands.
