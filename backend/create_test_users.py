import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from models.user import User
from dependencies.auth_deps import get_password_hash, create_access_token
import uuid

async def create_users():
    async with AsyncSessionLocal() as db:
        unique_a = str(uuid.uuid4())[:8]
        unique_b = str(uuid.uuid4())[:8]
        user_a = User(email=f"user_{unique_a}@example.com", name="User A", hashed_password=get_password_hash("pass"), role="USER", is_active=True)
        user_b = User(email=f"user_{unique_b}@example.com", name="User B", hashed_password=get_password_hash("pass"), role="USER", is_active=True)
        db.add(user_a)
        db.add(user_b)
        await db.commit()
        await db.refresh(user_a)
        await db.refresh(user_b)
        
        token_a = create_access_token(user_a.uuid, "USER")
        token_b = create_access_token(user_b.uuid, "USER")
        
        with open("tokens.txt", "w") as f:
            f.write(f"{token_a}\n{token_b}")

asyncio.run(create_users())
