import datetime
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import get_db
from models.user import User, RefreshToken
from schemas import UserRegister, UserLogin, UserResponse, TokenResponse, RefreshTokenRequest
from dependencies.auth_deps import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: Session = Depends(get_db)):
    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    # Check if duplicate email async-safely
    result = await db.execute(select(User).filter(User.email == payload.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    # Create new user
    hashed_pwd = get_password_hash(payload.password)
    new_user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hashed_pwd,
        role="USER",
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return UserResponse(
        id=new_user.uuid,
        email=new_user.email,
        name=new_user.name,
        role=new_user.role
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: Session = Depends(get_db)):
    result = await db.execute(select(User).filter(User.email == payload.email))
    user = result.scalars().first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive"
        )
    
    # Generate tokens
    access_token = create_access_token(user.uuid, user.role)
    refresh_token = create_refresh_token(user.uuid)
    
    # Save refresh token in DB
    db_refresh = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7),
        is_revoked=False
    )
    db.add(db_refresh)
    await db.commit()
    
    user_res = UserResponse(
        id=user.uuid,
        email=user.email,
        name=user.name,
        role=user.role
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_res
    )


@router.post("/logout")
async def logout(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    result = await db.execute(
        select(RefreshToken).filter(
            RefreshToken.token == payload.refresh_token,
            RefreshToken.is_revoked == False
        )
    )
    db_token = result.scalars().first()
    if db_token:
        db_token.is_revoked = True
        await db.commit()
    return {"success": True, "message": "Successfully logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        # Decode and verify refresh token
        decoded = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_uuid: str = decoded.get("user_id")
        token_type: str = decoded.get("type")
        if user_uuid is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token payload"
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Verify in DB async-safely
    token_result = await db.execute(
        select(RefreshToken).filter(
            RefreshToken.token == payload.refresh_token,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.datetime.utcnow()
        )
    )
    db_token = token_result.scalars().first()
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid, expired, or revoked"
        )
    
    # Fetch user
    user_result = await db.execute(select(User).filter(User.uuid == user_uuid))
    user = user_result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found"
        )
    
    # Generate new tokens
    new_access_token = create_access_token(user.uuid, user.role)
    new_refresh_token = create_refresh_token(user.uuid)
    
    # Revoke old token and save new token
    db_token.is_revoked = True
    db_new_refresh = RefreshToken(
        user_id=user.id,
        token=new_refresh_token,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7),
        is_revoked=False
    )
    db.add(db_new_refresh)
    await db.commit()
    
    user_res = UserResponse(
        id=user.uuid,
        email=user.email,
        name=user.name,
        role=user.role
    )
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_res
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.uuid,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role
    )
