from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from datetime import datetime
import os

NAVY  = colors.HexColor('#14213D')
AMBER = colors.HexColor('#fca311')
RED   = colors.HexColor('#ba1a1a')
GREEN = colors.HexColor('#27AE60')
CREAM = colors.HexColor('#fff8f4')
GRAY  = colors.HexColor('#534433')
LGRAY = colors.HexColor('#f0e0d1')

SEV_COLOR = {"P1":RED,"P2":AMBER,"P3":colors.HexColor('#006687'),"P4":GREEN}
EVENT_ICONS = {
    "crash_detected":"CRASH",
    "sos_triggered":"SOS",
    "ambulance_dispatched":"AMB",
    "ambulance_arrived":"ARR",
    "hospital_admitted":"HOSP",
    "report_generated":"RPT",
    "incident_created":"OPEN",
}


def generate_incident_pdf(incident, events) -> str:
    # Ensure reports directory exists inside current runtime folder
    os.makedirs("reports", exist_ok=True)
    short_id = incident.incident_id[:8].upper()
    pdf_path = f"reports/RoadSOS_Incident_{short_id}.pdf"

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm)

    styles   = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph("RoadSOS", ParagraphStyle(
        'H', fontSize=22, fontName='Helvetica-Bold', textColor=NAVY)))
    elements.append(Paragraph("Incident Report", ParagraphStyle(
        'T', fontSize=14, fontName='Helvetica-Bold', textColor=GRAY)))
    elements.append(Spacer(1, 4*mm))

    # Meta row
    sev_color = SEV_COLOR.get(incident.severity, GRAY)
    sub = ParagraphStyle('s', fontSize=10, fontName='Helvetica', textColor=GRAY)
    hd = Table([[
        Paragraph(f"<b>ID:</b> {short_id}", sub),
        Paragraph(f"<b>Generated:</b> {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}", sub),
        Paragraph(f"<b>Severity:</b> {incident.severity or 'Unknown'}",
            ParagraphStyle('sv', fontSize=10, fontName='Helvetica-Bold', textColor=sev_color)),
    ]], colWidths=[55*mm, 80*mm, 35*mm])
    hd.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),LGRAY),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
    ]))
    elements += [hd, Spacer(1,5*mm), HRFlowable(width="100%",thickness=1,color=LGRAY), Spacer(1,4*mm)]

    def heading(t):
        return Paragraph(t, ParagraphStyle('sh', fontSize=11, fontName='Helvetica-Bold',
            textColor=NAVY, spaceBefore=4, spaceAfter=4))

    def dtable(rows):
        t = Table(rows, colWidths=[45*mm, None])
        t.setStyle(TableStyle([
            ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),
            ('FONTNAME',(1,0),(1,-1),'Helvetica'),
            ('FONTSIZE',(0,0),(-1,-1),9),
            ('TEXTCOLOR',(0,0),(0,-1),NAVY),
            ('TEXTCOLOR',(1,0),(1,-1),GRAY),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
            ('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.white,CREAM]),
            ('LINEBELOW',(0,0),(-1,-2),0.25,LGRAY),
        ]))
        return t

    # Crash details
    elements.append(heading("Crash Details"))
    elements.append(dtable([
        ["Date & time",   str(incident.crash_timestamp)[:16] if incident.crash_timestamp else "Unknown"],
        ["Location",      incident.address or (f"{incident.latitude}, {incident.longitude}" if incident.latitude else "Unknown")],
        ["Severity",      incident.severity or "Unknown"],
        ["Speed at impact", f"{incident.speed_at_impact} km/h" if incident.speed_at_impact else "Unknown"],
    ]))
    elements.append(Spacer(1,5*mm))

    # Medical
    mp = incident.medical_profile or {}
    elements.append(heading("Medical Information"))
    elements.append(dtable([
        ["Name",       mp.get("full_name", mp.get("name", "Unknown"))],
        ["Blood type", mp.get("blood_type", mp.get("bloodType", "Unknown"))],
        ["Allergies",  ", ".join(mp.get("allergies",[]) or []) or "None"],
        ["Conditions", ", ".join(mp.get("conditions",[]) or []) or "None"],
        ["Medications",", ".join(mp.get("medications",[]) or []) or "None"],
    ]))
    elements.append(Spacer(1,5*mm))

    # Response
    elements.append(heading("Emergency Response"))
    elements.append(dtable([
        ["Ambulance", incident.ambulance_name or "Not dispatched"],
        ["Hospital",  incident.hospital_name  or "Unknown"],
    ]))
    elements.append(Spacer(1,5*mm))

    # Timeline
    elements.append(heading("Incident Timeline"))
    ev_sub = ParagraphStyle('ev', fontSize=9, fontName='Helvetica', textColor=GRAY)
    badge_s= ParagraphStyle('b',  fontSize=8, fontName='Helvetica-Bold',
                             textColor=NAVY, alignment=TA_CENTER)
    for ev in events:
        ts    = str(ev.timestamp)[:16]
        label = EVENT_ICONS.get(ev.event_type, "EVT")
        desc  = ev.description or ev.event_type.replace("_"," ").title()
        rt = Table([[Paragraph(f"<b>{label}</b>", badge_s),
                     Paragraph(f"<b>{ts}</b>  {desc}", ev_sub)]],
                   colWidths=[14*mm, None])
        rt.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(0,0),LGRAY),
            ('ALIGN',(0,0),(0,0),'CENTER'),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
            ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ]))
        elements += [rt, Spacer(1,2*mm)]

    # Photos
    if incident.photo_urls:
        elements += [Spacer(1,5*mm), heading("Photo Evidence")]
        for p in (incident.photo_urls or []):
            url  = p.get("url","") if isinstance(p,dict) else str(p)
            name = p.get("filename","photo") if isinstance(p,dict) else "photo"
            ts   = p.get("uploaded_at","")[:16] if isinstance(p,dict) else ""
            elements.append(Paragraph(f"• {name}  {ts}  {url}",
                ParagraphStyle('ph', fontSize=8, fontName='Helvetica',
                               textColor=GRAY, leftIndent=8)))

    # Footer
    elements += [Spacer(1,5*mm),
                 HRFlowable(width="100%",thickness=1,color=LGRAY),
                 Spacer(1,3*mm),
                 Paragraph("Auto-generated by RoadSOS. For emergencies call 112. "
                            "For insurance claims attach this document.",
                     ParagraphStyle('ft', fontSize=8, fontName='Helvetica',
                                    textColor=GRAY, alignment=TA_CENTER))]
    doc.build(elements)
    return pdf_path
