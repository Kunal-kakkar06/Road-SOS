# State FIR Guidelines Service Helper

def get_compliance_checklist(state: str) -> list:
    """
    Returns standard legal document lists required for filing an FIR in specific Indian states.
    """
    default_docs = [
        "Government Issued Photo ID (Aadhaar/PAN/DL)",
        "Details of vehicle registration (RC copy)",
        "Incident details (Time, GPS coordinates)",
        "Ambulance Dispatch record (from RoadSOS)",
        "Hospital Admission summary / Triage report",
        "Evidence Photos showing vehicle crash damage"
    ]
    
    checklists = {
        "Karnataka": default_docs + ["Karnataka Police e-lost/e-FIR online registration confirmation"],
        "Maharashtra": default_docs + ["Maharashtra Police Citizen Portal account record"],
        "Delhi": default_docs + ["Delhi Police Mobile App MV Theft/Simple Accident e-FIR reference"]
    }
    
    return checklists.get(state, default_docs)
