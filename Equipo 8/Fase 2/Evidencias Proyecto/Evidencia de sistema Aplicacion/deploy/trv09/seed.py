"""Crea únicamente la cuenta del laboratorio, sin modificar otras bases."""
import asyncio
from pathlib import Path
from sqlalchemy import select
from app.database import get_session_maker, dispose_engine
from app.models import Role, User
from app.services.auth_service import AuthService

async def main():
    async with get_session_maker()() as db:
        user = await db.scalar(select(User).where(User.email == "admin.trv09@example.org"))
        if user is None:
            role = await db.scalar(select(Role).where(Role.name == "ADMIN"))
            if role is None:
                raise RuntimeError("Falta aplicar las migraciones")
            db.add(User(email="admin.trv09@example.org", full_name="Administrador TRV-09", role_id=role.id, is_active=True, hashed_password=AuthService.hash_password(Path("/run/secrets/demo_password").read_text().strip())))
            await db.commit()
        print("Cuenta del laboratorio disponible: admin.trv09@example.org")
    await dispose_engine()

if __name__ == "__main__":
    asyncio.run(main())
