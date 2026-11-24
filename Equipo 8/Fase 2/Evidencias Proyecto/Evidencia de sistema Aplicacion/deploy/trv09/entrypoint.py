"""Carga secretos montados, espera dependencias y ejecuta un único proceso."""
import asyncio
import os
from pathlib import Path
import sys
import time

if os.environ.get("ENVIRONMENT") != "demo":
    raise SystemExit("Esta imagen es exclusiva del laboratorio TRV-09")

def read_secret(name):
    return Path("/run/secrets", name).read_text().strip()

os.environ["SECRET_KEY"] = read_secret("jwt_key")
os.environ["DATABASE_URL"] = "postgresql+asyncpg://corestream:" + read_secret("db_password") + "@postgres:5432/corestream_trv09"
os.environ["REDIS_URL"] = "redis://:" + read_secret("redis_password") + "@redis:6379/0"

async def wait_dependencies():
    import asyncpg
    from redis.asyncio import Redis
    for attempt in range(60):
        try:
            connection = await asyncio.wait_for(asyncpg.connect(os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")), timeout=3)
            await connection.close()
            redis = Redis.from_url(os.environ["REDIS_URL"], socket_connect_timeout=3, socket_timeout=3)
            try:
                await redis.ping()
            finally:
                await redis.aclose()
            return
        except Exception:
            if attempt == 59:
                raise SystemExit("PostgreSQL o Redis no estuvieron disponibles a tiempo")
            await asyncio.sleep(2)

asyncio.run(wait_dependencies())
# No hay migraciones ni creación de usuarios al arrancar cada réplica.
os.execvp(sys.argv[1], sys.argv[1:])
