import os
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter(prefix="/api/voice-guidance", tags=["Voice Guidance"])

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(base_dir, 'data', 'first_aid_tree.json')

def load_tree():
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {}

class GenerateRequest(BaseModel):
    injury_type: str
    severity: str
    user_location: Optional[Dict[str, float]] = None

class DecisionTreeRequest(BaseModel):
    current_node: str
    user_answer: str

class ResponderRequest(BaseModel):
    lat: float
    lng: float
    radius: int = 500

@router.post("/generate")
def generate_guidance(req: GenerateRequest):
    tree = load_tree()
    injury = req.injury_type.lower()
    
    if injury not in tree:
        raise HTTPException(status_code=404, detail="Injury type not found in guidance tree")
    
    # Simple mapping logic for prototype based on severity
    severity_mapping = {
        "minor": f"{injury}_minor",
        "moderate": f"{injury}_moderate",
        "severe": f"{injury}_severe"
    }
    
    # Try to find an outcome that matches
    outcome_key = severity_mapping.get(req.severity.lower())
    
    outcomes = tree[injury].get("outcomes", {})
    if outcome_key and outcome_key in outcomes:
        outcome = outcomes[outcome_key]
        return {
            "steps": outcome.get("steps", []),
            "estimated_time": len(outcome.get("steps", [])) * 2, # Rough estimate
            "audio_file_ids": outcome.get("audio_ids", []),
            "auto_trigger_sos": outcome.get("auto_trigger_sos", False)
        }
    
    # Fallback to returning the first question to start the tree
    questions = tree[injury].get("questions", [])
    if questions:
        return {
            "steps": [],
            "estimated_time": 5,
            "audio_file_ids": [],
            "auto_trigger_sos": False,
            "decision_tree_start": questions[0]
        }
        
    raise HTTPException(status_code=400, detail="Could not generate guidance")

@router.get("/audio/{instruction_id}")
def get_audio(instruction_id: str):
    audio_path = os.path.join(base_dir, 'static', 'audio', f"{instruction_id}.mp3")
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(audio_path, media_type="audio/mpeg")

@router.post("/decision-tree")
def decision_tree_progress(req: DecisionTreeRequest):
    tree = load_tree()
    # The current_node is expected to be the injury type (e.g. "bleeding")
    injury = req.current_node.lower()
    
    if injury not in tree:
        raise HTTPException(status_code=404, detail="Injury type not found")
    
    # In a real app, current_node might be a specific question ID.
    # For this prototype, we check the user's answer against the first question's options.
    questions = tree[injury].get("questions", [])
    outcomes = tree[injury].get("outcomes", {})
    
    if not questions:
        raise HTTPException(status_code=400, detail="No questions available")
        
    q1 = questions[0]
    
    try:
        idx = q1["options"].index(req.user_answer)
        next_step = q1["next"][idx]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid answer for current node")
        
    # Check if next_step is an outcome or another question
    if next_step in outcomes:
        outcome = outcomes[next_step]
        return {
            "next_question": None,
            "options": [],
            "final_instruction": {
                "steps": outcome.get("steps", []),
                "audio_file_ids": outcome.get("audio_ids", []),
                "auto_trigger_sos": outcome.get("auto_trigger_sos", False)
            },
            "is_complete": True
        }
    
    # Otherwise, it would be another question (not implemented in our simple JSON)
    return {
        "next_question": "Unknown next step",
        "options": [],
        "final_instruction": None,
        "is_complete": False
    }

@router.post("/nearby-responders")
def nearby_responders(req: ResponderRequest):
    # TODO: Firebase + Geofencing integration
    # Returning mock data for now
    return {
        "responders": [
            {
                "name": "Alex M. (Off-duty EMT)",
                "distance_m": 120,
                "eta_min": 2,
                "cert_level": "Paramedic"
            },
            {
                "name": "Sarah J.",
                "distance_m": 350,
                "eta_min": 5,
                "cert_level": "CPR Certified"
            }
        ]
    }
