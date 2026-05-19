import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import engine, Base
from routers import ambulance, dispatch

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create all tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created/ensured on startup.")
    yield

app = FastAPI(
    title="RoadSOS Emergency Backend API",
    description="Backend API for emergency road assistance, real-time tracking, dispatch routing and triage management.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware allowing all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(ambulance.router)
app.include_router(dispatch.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to RoadSOS Emergency API Backend Service",
        "status": "online",
        "endpoints": {
            "api_doc": "/docs",
            "request_ambulance": "POST /api/ambulance/request",
            "nearby_ambulances": "GET /api/ambulance/nearby",
            "update_location": "PATCH /api/ambulance/{id}/location",
            "get_dispatch": "GET /api/dispatch/{id}",
            "update_dispatch_status": "PATCH /api/dispatch/{id}/status"
        }
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
