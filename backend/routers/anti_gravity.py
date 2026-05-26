import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Optional, Any

router = APIRouter(prefix="/api/anti-gravity", tags=["Anti-Gravity"])
logger = logging.getLogger("roadsos.antigravity")

class SensorData(BaseModel):
    x: float
    y: float
    z: float
    timestamp: int

class LocationData(BaseModel):
    lat: float
    lng: float

class FallDetectedRequest(BaseModel):
    accelerometer_data: SensorData
    gyroscope_data: Optional[SensorData] = None
    impact_force: float
    location: Optional[LocationData] = None
    user_id: str

class CancelAlertRequest(BaseModel):
    alert_id: str
    user_id: str

@router.post("/fall-detected")
def fall_detected(req: FallDetectedRequest):
    # Simplified backend logic for prototype.
    # The actual detection logic is heavily pushed to the frontend/service worker
    # to avoid spamming the backend with 100ms sensor data.
    # The backend confirms the fall severity based on the reported impact force.
    
    is_fall = False
    confidence = 0.0
    severity = "low"
    auto_sos_triggered = False
    countdown_seconds = 30
    
    # Impact force in Gs
    impact = req.impact_force
    
    if impact > 3.5:
        is_fall = True
        confidence = min((impact / 8.0) * 100, 99.9)  # Cap at 99.9%
        
        if impact > 8.0:
            severity = "critical"
            countdown_seconds = 10
            auto_sos_triggered = True
        elif impact > 5.0:
            severity = "high"
            countdown_seconds = 20
            auto_sos_triggered = True
        else:
            severity = "medium"
            countdown_seconds = 30
            auto_sos_triggered = True
            
        logger.warning(f"FALL DETECTED for user {req.user_id}: {impact}G impact. Severity: {severity}")
        
    return {
        "is_fall": is_fall,
        "confidence": confidence,
        "severity": severity,
        "auto_sos_triggered": auto_sos_triggered,
        "countdown_seconds": countdown_seconds,
        "alert_id": f"alert_{req.timestamp if hasattr(req, 'timestamp') else '0'}"
    }

@router.post("/cancel-alert")
def cancel_alert(req: CancelAlertRequest):
    logger.info(f"Fall alert {req.alert_id} cancelled by user {req.user_id}")
    return {"cancelled": True}

@router.get("/sensor-calibration")
def sensor_calibration():
    return {
        "thresholds": {
            "impact_min": 3.5,
            "freefall_duration_ms": 100,
            "stillness_variance": 0.5,
            "stillness_duration_s": 5
        }
    }

@router.post("/test-fall")
def test_fall():
    return {
        "is_fall": True,
        "confidence": 95.5,
        "severity": "high",
        "auto_sos_triggered": True,
        "countdown_seconds": 10,
        "alert_id": "test_alert_123"
    }
