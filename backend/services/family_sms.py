from twilio.rest import Client
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from typing import List
import os

load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_PHONE_NUMBER")

is_configured = (
    account_sid and "your_" not in account_sid and
    auth_token and "your_" not in auth_token and
    TWILIO_FROM and "your_" not in TWILIO_FROM
)

if is_configured:
    _client = Client(account_sid, auth_token)
else:
    _client = None
    print("[Family SMS] Twilio credentials are not set/valid. Falling back to console logging.")


def build_family_alert(
    patient_name:  str,
    severity:      str,
    latitude:      float,
    longitude:     float,
    tracking_url:  str,
    delayed:       bool = False,
) -> str:
    maps_url  = f"https://maps.google.com/?q={latitude},{longitude}"
    name      = patient_name or "Someone you know"
    sev_label = {
        "P1": "CRITICAL — high-speed impact",
        "P2": "SERIOUS — significant crash",
        "P3": "MODERATE — possible collision",
        "P4": "MINOR — low-severity event",
    }.get(severity, "Unknown severity")

    delay_note = (
        "\n⚠ NOTE: Alert was delayed — device was offline when SOS triggered."
        if delayed else ""
    )

    return "\n".join([
        f"🚨 ROADSOS FAMILY ALERT",
        f"{name} has been in a road accident.{delay_note}",
        f"",
        f"Severity: {sev_label}",
        f"",
        f"📍 Last known location:",
        f"{maps_url}",
        f"",
        f"🔴 Track live location:",
        f"{tracking_url}",
        f"",
        f"Please call emergency services (112) if needed.",
        f"RoadSOS Emergency Alert System",
    ])


async def send_family_alert_sms(
    contacts:     List[dict],
    patient_name: str,
    severity:     str,
    latitude:     float,
    longitude:    float,
    tracking_url: str,
    session_id:   str,
    db:           Session,
    delayed:      bool = False,
) -> bool:
    message = build_family_alert(
        patient_name, severity, latitude, longitude, tracking_url, delayed
    )
    sent = 0
    notified = []

    for contact in contacts:
        phone = contact.get("phone") or contact.get("phone_number")
        if not phone:
            continue
        
        sms_sent = False
        if is_configured:
            try:
                _client.messages.create(
                    body  = message,
                    from_ = TWILIO_FROM,
                    to    = phone,
                )
                sms_sent = True
                sent += 1
                print(f"[FamilyAlert SMS] Sent to {contact.get('name')} ({phone})")
            except Exception as e:
                print(f"[FamilyAlert SMS] Failed for {phone}: {e}")
        else:
            # Fallback console visual logger
            sms_sent = True
            sent += 1
            print("\n" + "="*50)
            print(f"[MOCK SMS FALLBACK SENT TO: {contact.get('name')} ({phone})]")
            print(message)
            print("="*50 + "\n")

        notified.append({**contact, "sms_sent": sms_sent})

    # Update session SMS status
    from models.tracking_session import TrackingSession
    session = db.query(TrackingSession).filter(
        TrackingSession.session_id == session_id
    ).first()
    if session:
        session.sms_sent          = sent > 0
        session.contacts_notified = notified
        db.commit()

    print(f"[FamilyAlert] {sent}/{len(contacts)} SMS simulated/sent")
    return sent > 0
