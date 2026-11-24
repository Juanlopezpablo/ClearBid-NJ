"""Identificador de instancia solo en la imagen de demostración TRV-09."""
import socket
from app.main import app

@app.middleware("http")
async def identify_instance(request, call_next):
    response = await call_next(request)
    response.headers["X-CoreStream-Instance"] = socket.gethostname()
    return response
