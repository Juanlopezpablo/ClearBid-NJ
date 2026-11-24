"""Prueba funcional y carga acotada del laboratorio; nunca imprime credenciales."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time
import httpx

BASE = "http://web:8080"
STATE = Path("/app/storage/trv09-sample.json")
CONTENT = b"TRV-09: evidencia compartida entre replicas del backend."

def request(client, method, path, **kwargs):
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path.split('?')[0]} respondio {response.status_code}")
    return response

def session():
    client = httpx.Client(base_url=BASE, timeout=15, headers={"Connection": "close"})
    data = request(client, "POST", "/api/auth/login", json={"email": "admin.trv09@example.org", "password": Path("/run/secrets/demo_password").read_text().strip()}).json()
    client.headers["Authorization"] = "Bearer " + data["access_token"]
    return client

def prepare(client):
    if STATE.exists():
        state = json.loads(STATE.read_text())
        request(client, "GET", "/api/tickets/" + state["ticket_id"])
        return state
    application = request(client, "POST", "/api/applications/", json={"name": "Laboratorio TRV-09", "description": "Datos exclusivos de demostracion"}).json()
    epic = request(client, "POST", "/api/epics/", json={"application_id": application["id"], "title": "Escalabilidad local"}).json()
    ticket = request(client, "POST", "/api/tickets/", json={"epic_id": epic["id"], "title": "TRV-09: ticket compartido", "description": "Este ticket debe ser visible desde cualquier replica."}).json()
    signed = request(client, "POST", "/api/documents/upload-url", json={"filename": "evidencia-trv09.txt", "content_type": "text/plain", "size": len(CONTENT), "ticket_id": ticket["id"]}).json()
    request(client, "PUT", signed["url"], content=CONTENT, headers=signed["headers"])
    document = request(client, "POST", "/api/documents/confirm", json={"upload_token": signed["upload_token"]}).json()
    state = {"application_id": application["id"], "ticket_id": ticket["id"], "document_id": document["id"]}
    STATE.write_text(json.dumps(state))
    return state

def measure(client, state, replicas):
    def read_ticket(_):
        start = time.perf_counter()
        response = client.get("/api/tickets/" + state["ticket_id"])
        elapsed = (time.perf_counter() - start) * 1000
        ok = response.status_code == 200 and response.json().get("id") == state["ticket_id"]
        return ok, elapsed, response.headers.get("X-CoreStream-Instance", "sin-identificador")
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(read_ticket, range(120)))
    duration = time.perf_counter() - start
    instances = Counter(item[2] for item in results)
    failures = sum(not item[0] for item in results)
    if failures or "sin-identificador" in instances or len(instances) != replicas:
        raise RuntimeError(f"Carga no valida: errores={failures}, instancias={len(instances)}, esperadas={replicas}")
    download = request(client, "GET", f"/api/documents/{state['document_id']}/download-url").json()["url"]
    file_instances = set()
    for _ in range(30):
        response = request(client, "GET", download)
        if response.content != CONTENT:
            raise RuntimeError("Archivo inconsistente entre replicas")
        file_instances.add(response.headers.get("X-CoreStream-Instance"))
    if len(file_instances) != replicas:
        raise RuntimeError("La descarga no alcanzo todas las replicas")
    # La cookie emitida por una instancia debe poder renovarse en otra.
    csrf = client.cookies.get("csrf_token")
    renewed = request(client, "POST", "/api/auth/refresh", headers={"x-csrf-token": csrf or ""})
    token = renewed.json()["access_token"]
    request(client, "GET", "/api/auth/me", headers={"Authorization": "Bearer " + token})
    elapsed = sorted(item[1] for item in results)
    return {"utc": datetime.now(timezone.utc).isoformat(), "replicas": replicas, "requests": len(results), "concurrency": 6, "errors": failures, "duration_seconds": round(duration, 3), "requests_per_second": round(len(results) / duration, 2), "median_ms": round(statistics.median(elapsed), 2), "p95_ms": round(elapsed[int((len(elapsed)-1)*.95)], 2), "requests_by_instance": dict(instances), "file_instances": sorted(file_instances), "shared_file_ok": True, "session_refresh_ok": True, "ticket_id": state["ticket_id"]}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--replicas", type=int, choices=[1, 2, 3], default=1)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    client = session()
    try:
        state = prepare(client)
        result = {"prepared": True, "ticket_id": state["ticket_id"]} if args.prepare else measure(client, state, args.replicas)
        print(json.dumps(result))
    finally:
        client.close()
