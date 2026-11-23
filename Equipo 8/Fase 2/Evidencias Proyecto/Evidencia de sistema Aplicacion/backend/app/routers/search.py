"""NEW-13: búsqueda autenticada, plana y paginada por tipo de recurso."""
from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import Text, cast, func, literal, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Application, Document, Epic, Incident, Ticket
from app.routers.documents import active_user

router = APIRouter(prefix="/api/search", tags=["Búsqueda global"])

def snippet(text: str, query: str) -> str:
    text = " ".join((text or "").split())
    index = text.lower().find(query.lower())
    start = max(0, index - 80) if index >= 0 else 0
    end = start + 260
    return ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")

@router.get("")
async def global_search(
    q: str = Query(..., min_length=2, max_length=200),
    kind: Literal["all", "ticket", "application", "epic", "incident", "document"] = "all",
    skip: int = Query(0, ge=0, le=10000),
    limit: int = Query(25, ge=1, le=50),
    current_user=Depends(active_user),
    db: AsyncSession = Depends(get_db),
):
    query = q.strip()
    if len(query) < 2:
        return {"items": [], "total": 0}
    # La búsqueda respeta el acceso de lectura existente: usuarios activos
    # pueden consultar estos recursos. No expone usuarios, claves ni rutas de almacenamiento.
    specs = [("ticket", Ticket, Ticket.title, Ticket.description),
             ("application", Application, Application.name, Application.description),
             ("epic", Epic, Epic.title, Epic.description),
             ("incident", Incident, Incident.title, Incident.description),
             ("document", Document, Document.filename, Document.search_text)]
    searches = []
    for resource, model, title, body in specs:
        if kind not in ("all", resource):
            continue
        matches = or_(title.icontains(query, autoescape=True), body.icontains(query, autoescape=True), cast(model.id, Text).icontains(query, autoescape=True))
        searches.append(select(literal(resource).label("kind"), cast(model.id, Text).label("id"), title.label("title"), body.label("body"), model.created_at.label("created_at")).where(matches))
    results = union_all(*searches).subquery()
    total = await db.scalar(select(func.count()).select_from(results))
    rows = (await db.execute(select(results).order_by(results.c.created_at.desc(), results.c.kind, results.c.id).offset(skip).limit(limit))).mappings().all()
    return {"total": total, "items": [{"id": row["id"], "kind": row["kind"], "title": row["title"], "snippet": snippet(row["body"], query)} for row in rows]}
