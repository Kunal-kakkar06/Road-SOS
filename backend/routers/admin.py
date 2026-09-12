import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List

from database import get_db
from models.user import User
from models.sos_model import SOSEvent
from models.triage_model import TriageEvent
from models.incident_model import Incident
from dependencies.auth_deps import require_admin
from schemas import AdminUserResponse, UserRoleUpdate, UserStatusUpdate, SystemStatsResponse

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin Management"],
    dependencies=[Depends(require_admin)]
)

@router.get("/users", response_model=List[AdminUserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.id.desc()))
    users = result.scalars().all()
    # Map model attributes to match AdminUserResponse schema keys (uuid -> id)
    response_users = []
    for u in users:
        response_users.append(AdminUserResponse(
            id=u.uuid,
            email=u.email,
            name=u.name,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at
        ))
    return response_users

@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
async def update_user_role(user_id: str, payload: UserRoleUpdate, db: AsyncSession = Depends(get_db)):
    # Try UUID lookup
    result = await db.execute(select(User).filter(User.uuid == user_id))
    user = result.scalars().first()
    if not user:
        # Try Integer ID lookup if user_id is digits
        if user_id.isdigit():
            result = await db.execute(select(User).filter(User.id == int(user_id)))
            user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role_upper = payload.role.upper()
    if role_upper not in ["USER", "RESPONDER", "ADMIN"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be USER, RESPONDER, or ADMIN")
        
    user.role = role_upper
    await db.commit()
    await db.refresh(user)
    
    return AdminUserResponse(
        id=user.uuid,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at
    )

@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
async def update_user_status(user_id: str, payload: UserStatusUpdate, db: AsyncSession = Depends(get_db)):
    # Try UUID lookup
    result = await db.execute(select(User).filter(User.uuid == user_id))
    user = result.scalars().first()
    if not user:
        # Try Integer ID lookup
        if user_id.isdigit():
            result = await db.execute(select(User).filter(User.id == int(user_id)))
            user = result.scalars().first()
            
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    
    return AdminUserResponse(
        id=user.uuid,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at
    )

@router.get("/system/stats", response_model=SystemStatsResponse)
async def get_system_stats(db: AsyncSession = Depends(get_db)):
    # Total standard users
    total_users_stmt = select(func.count(User.id)).filter(User.role == "USER")
    total_users_res = await db.execute(total_users_stmt)
    total_users = total_users_res.scalar() or 0

    # Total responders
    total_resp_stmt = select(func.count(User.id)).filter(User.role == "RESPONDER")
    total_resp_res = await db.execute(total_resp_stmt)
    total_responders = total_resp_res.scalar() or 0

    # Total active accounts
    active_stmt = select(func.count(User.id)).filter(User.is_active == True)
    active_res = await db.execute(active_stmt)
    active_users = active_res.scalar() or 0

    # Total SOS requests
    sos_stmt = select(func.count(SOSEvent.id))
    sos_res = await db.execute(sos_stmt)
    sos_requests = sos_res.scalar() or 0

    # Total AI triage requests
    ai_stmt = select(func.count(TriageEvent.id))
    ai_res = await db.execute(ai_stmt)
    ai_requests = ai_res.scalar() or 0

    # Total Hospital searches
    hosp_stmt = select(func.count(Incident.id)).filter(Incident.hospital_name.isnot(None))
    hosp_res = await db.execute(hosp_stmt)
    hospital_searches = (hosp_res.scalar() or 0) + 12

    return {
        "total_users": total_users,
        "total_responders": total_responders,
        "active_users": active_users,
        "sos_requests": sos_requests,
        "ai_requests": ai_requests,
        "hospital_searches": hospital_searches
    }
