import asyncio
import sys
from sqlalchemy.future import select
from database import AsyncSessionLocal
from models.user import User
from dependencies.auth_deps import get_password_hash

DEMO_ACCOUNTS = [
    {
        "email": "user@roadsos.com",
        "name": "Standard Test User",
        "password": "User@12345",
        "role": "USER"
    },
    {
        "email": "responder@roadsos.com",
        "name": "First Responder",
        "password": "Responder@12345",
        "role": "RESPONDER"
    },
    {
        "email": "admin@roadsos.com",
        "name": "System Administrator",
        "password": "Admin@12345",
        "role": "ADMIN"
    }
]

async def seed_demo_accounts():
    async with AsyncSessionLocal() as db:
        for acc in DEMO_ACCOUNTS:
            res = await db.execute(select(User).filter(User.email == acc["email"]))
            existing_user = res.scalars().first()
            
            hashed_pwd = get_password_hash(acc["password"])
            
            if existing_user:
                existing_user.name = acc["name"]
                existing_user.role = acc["role"]
                existing_user.hashed_password = hashed_pwd
                existing_user.is_active = True
                print(f"[UPDATED] {acc['role']} account: {acc['email']}")
            else:
                new_user = User(
                    email=acc["email"],
                    name=acc["name"],
                    hashed_password=hashed_pwd,
                    role=acc["role"],
                    is_active=True
                )
                db.add(new_user)
                print(f"[CREATED] {acc['role']} account: {acc['email']}")
                
        await db.commit()
        print("\nAll demo accounts seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_demo_accounts())
