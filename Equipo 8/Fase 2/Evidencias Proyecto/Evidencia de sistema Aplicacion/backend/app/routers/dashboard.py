"""APP-08: resumen inicial según identidad, rol y equipo seleccionado."""
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Epic, Incident, Sprint, Team, Ticket, User
from app.routers.documents import active_user
from app.services.ticket_permissions import get_role_name

router = APIRouter(prefix="/api/dashboard", tags=["Inicio"])

@router.get("")
async def dashboard(
    team_id: UUID | None = None,
    focus: Literal["pending", "in_progress", "blocked", "overdue", "upcoming"] = "pending",
    skip: int = Query(0, ge=0, le=10000),
    limit: int = Query(10, ge=1, le=25),
    user: User = Depends(active_user),
    db: AsyncSession = Depends(get_db),
):
    role = get_role_name(user)
    if role not in {"ADMIN", "TEAM_LEADER", "DEVELOPER"}:
        raise HTTPException(403, "Rol no compatible con el panel de inicio")
    manager = role != "DEVELOPER"
    if team_id and not manager:
        raise HTTPException(403, "El panel personal no permite seleccionar otros equipos")
    team = await db.get(Team, team_id) if team_id else None
    if team_id and team is None:
        raise HTTPException(404, "Equipo no encontrado")
    # Team no define líderes responsables: los gestores seleccionan un equipo
    # entre los que ya pueden consultar. Nunca se inventa una pertenencia.
    scope = []
    if not manager:
        scope.append(Ticket.assignee_id == user.id)
    if team_id:
        scope.append(Ticket.epic_id.in_(select(Epic.id).where(Epic.team_id == team_id)))
    now = datetime.now(timezone.utc)
    pending = Ticket.status.notin_(["COMPLETED", "RESOLVED"])
    conditions = {
        "pending": pending,
        "in_progress": Ticket.status.in_(["IN_PROGRESS", "INVESTIGATING"]),
        "blocked": Ticket.status.in_(["BLOCKED", "BLOCKED_QUESTION"]),
        "overdue": and_(pending, Ticket.due_date < now),
        "upcoming": and_(pending, Ticket.due_date >= now, Ticket.due_date <= now + timedelta(days=7)),
    }
    counts = (await db.execute(select(*(func.count(Ticket.id).filter(condition).label(name) for name, condition in conditions.items())).where(*scope))).mappings().one()
    filtered = [*scope, conditions[focus]]
    total = await db.scalar(select(func.count(Ticket.id)).where(*filtered))
    ordering = [case((Ticket.due_date < now, 0), else_=1), case((Ticket.priority == "URGENT", 0), (Ticket.priority == "HIGH", 1), (Ticket.priority == "MEDIUM", 2), else_=3), Ticket.due_date.asc().nulls_last(), Ticket.created_at.desc(), Ticket.id]
    if focus == "upcoming":
        ordering = [Ticket.due_date.asc(), Ticket.id]
    tickets = (await db.scalars(select(Ticket).where(*filtered).order_by(*ordering).offset(skip).limit(limit))).all()
    # El avance del sprint usa solamente los tickets comprendidos en el panel.
    sprint_counts = select(Sprint.id, Sprint.name, Sprint.application_id, Sprint.end_date,
        func.count(Ticket.id).label("total"),
        func.count(Ticket.id).filter(Ticket.status == "COMPLETED").label("completed")
    ).outerjoin(Ticket, and_(Ticket.sprint_id == Sprint.id, *scope)).where(Sprint.status == "ACTIVE").group_by(Sprint.id)
    if scope:
        sprint_counts = sprint_counts.having(func.count(Ticket.id) > 0)
    sprint_total = await db.scalar(select(func.count()).select_from(sprint_counts.subquery()))
    sprints = (await db.execute(sprint_counts.order_by(Sprint.end_date, Sprint.id).limit(5))).mappings().all()
    # Una incidencia se relaciona con una aplicación, no con un equipo.
    incidents_available = team_id is None
    incident_count, incidents = None, []
    if incidents_available:
        incident_scope = [Incident.status != "RESOLVED"]
        if not manager:
            incident_scope.append(Incident.assigned_to_id == user.id)
        incident_count = await db.scalar(select(func.count(Incident.id)).where(*incident_scope))
        incidents = (await db.scalars(select(Incident).where(*incident_scope).order_by(Incident.severity, Incident.created_at.desc(), Incident.id).limit(5))).all()
    teams = (await db.execute(select(Team.id, Team.name).order_by(Team.name, Team.id))).all() if manager else []
    return {
        "role": role, "scope": "team" if team else ("general" if manager else "personal"),
        "team_id": str(team.id) if team else None, "team_name": team.name if team else None,
        "teams": [{"id": str(t.id), "name": t.name} for t in teams],
        "generated_at": now, "metrics": dict(counts), "focus": focus,
        "tickets": {"total": total, "skip": skip, "limit": limit, "items": [{"id": str(t.id), "title": t.title, "status": t.status, "priority": t.priority, "due_date": t.due_date, "ticket_type": t.ticket_type} for t in tickets]},
        "active_sprints": {"total": sprint_total, "items": [{"id": str(s["id"]), "name": s["name"], "application_id": str(s["application_id"]), "end_date": s["end_date"], "total_tickets": s["total"], "completed_tickets": s["completed"], "progress": round(s["completed"] * 100 / s["total"], 1) if s["total"] else 0} for s in sprints]},
        "incidents": {"available": incidents_available, "total": incident_count, "items": [{"id": str(i.id), "title": i.title, "severity": i.severity, "status": i.status, "description": (i.description or "")[:1000]} for i in incidents]},
    }
