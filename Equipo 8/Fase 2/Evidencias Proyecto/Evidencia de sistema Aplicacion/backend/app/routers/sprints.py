"""Planificación, ejecución y cierre de iteraciones de desarrollo."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import Application, Epic, Sprint, Ticket, TicketStatus, TicketType, User
from app.schemas.sprint import SprintCreate, SprintPage, SprintPlan, SprintResponse
from app.schemas.ticket import TicketResponse, TicketSearchResponse
from app.services.ticket_permissions import require_admin_or_leader

router = APIRouter(prefix="/api/sprints", tags=["Sprints"])


async def lock_sprint(db: AsyncSession, sprint_id: UUID) -> Sprint:
    application_id = await db.scalar(select(Sprint.application_id).where(Sprint.id == sprint_id))
    if application_id is None:
        raise HTTPException(404, "Sprint no encontrado")
    # Un orden común de bloqueo serializa la planificación de una aplicación.
    await db.execute(select(Application.id).where(Application.id == application_id).with_for_update())
    sprint = await db.scalar(select(Sprint).where(Sprint.id == sprint_id).with_for_update().execution_options(populate_existing=True))
    if sprint is None:
        raise HTTPException(404, "Sprint no encontrado")
    return sprint


async def responses(db: AsyncSession, sprints: list[Sprint]) -> list[SprintResponse]:
    if not sprints:
        return []
    counts = (await db.execute(select(
        Ticket.sprint_id, func.count(Ticket.id),
        func.sum(case((Ticket.status == TicketStatus.COMPLETED, 1), else_=0)),
    ).where(Ticket.sprint_id.in_([s.id for s in sprints])).group_by(Ticket.sprint_id))).all()
    totals = {row[0]: (row[1], row[2]) for row in counts}
    output = []
    for sprint in sprints:
        total, completed = totals.get(sprint.id, (0, 0))
        if sprint.status == "FINISHED":
            total, completed = sprint.closed_total or 0, sprint.closed_completed or 0
        output.append(SprintResponse(
            id=sprint.id, application_id=sprint.application_id, name=sprint.name, goal=sprint.goal,
            start_date=sprint.start_date, end_date=sprint.end_date, status=sprint.status,
            started_at=sprint.started_at, finished_at=sprint.finished_at,
            total_tickets=total, completed_tickets=completed,
            progress=round(completed * 100 / total, 1) if total else 0,
            released_tickets=(total - completed) if sprint.status == "FINISHED" else 0,
        ))
    return output


@router.get("", response_model=SprintPage)
async def list_sprints(application_id: UUID, skip: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
                       user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if await db.get(Application, application_id) is None:
        raise HTTPException(404, "Aplicación no encontrada")
    query = select(Sprint).where(Sprint.application_id == application_id)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    items = (await db.scalars(query.order_by(Sprint.start_date.desc(), Sprint.id).offset(skip).limit(limit))).all()
    return {"items": await responses(db, items), "total": total, "skip": skip, "limit": limit}


@router.post("", response_model=SprintResponse, status_code=201)
async def create_sprint(data: SprintCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_admin_or_leader(user)
    app = await db.scalar(select(Application).where(Application.id == data.application_id).with_for_update())
    if app is None:
        raise HTTPException(404, "Aplicación no encontrada")
    sprint = Sprint(**data.model_dump())
    db.add(sprint)
    await db.commit()
    await db.refresh(sprint)
    return (await responses(db, [sprint]))[0]


@router.get("/{sprint_id}", response_model=SprintResponse)
async def get_sprint(sprint_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sprint = await db.get(Sprint, sprint_id)
    if sprint is None:
        raise HTTPException(404, "Sprint no encontrado")
    return (await responses(db, [sprint]))[0]


@router.put("/{sprint_id}", response_model=SprintResponse)
async def edit_sprint(sprint_id: UUID, data: SprintPlan, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_admin_or_leader(user)
    sprint = await lock_sprint(db, sprint_id)
    if sprint.status != "PLANNED":
        raise HTTPException(409, "Solo se puede editar el plan antes de iniciar el sprint")
    for key, value in data.model_dump().items():
        setattr(sprint, key, value)
    await db.commit()
    await db.refresh(sprint)
    return (await responses(db, [sprint]))[0]


@router.post("/{sprint_id}/start", response_model=SprintResponse)
async def start_sprint(sprint_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_admin_or_leader(user)
    sprint = await lock_sprint(db, sprint_id)
    if sprint.status != "PLANNED":
        raise HTTPException(409, "Solo se puede iniciar un sprint planificado")
    active = await db.scalar(select(Sprint.id).where(Sprint.application_id == sprint.application_id, Sprint.status == "ACTIVE"))
    if active:
        raise HTTPException(409, "La aplicación ya tiene un sprint activo")
    if not await db.scalar(select(Ticket.id).where(Ticket.sprint_id == sprint.id).limit(1)):
        raise HTTPException(409, "Agrega al menos un ticket antes de iniciar el sprint")
    sprint.status = "ACTIVE"
    sprint.started_at = datetime.now(timezone.utc)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(409, "La aplicación ya tiene un sprint activo") from error
    await db.refresh(sprint)
    return (await responses(db, [sprint]))[0]


@router.post("/{sprint_id}/finish", response_model=SprintResponse)
async def finish_sprint(sprint_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_admin_or_leader(user)
    sprint = await lock_sprint(db, sprint_id)
    if sprint.status != "ACTIVE":
        raise HTTPException(409, "Solo se puede finalizar un sprint activo")
    # Bloquear las filas evita leer un estado intermedio durante un cierre.
    tickets = (await db.scalars(select(Ticket).where(Ticket.sprint_id == sprint.id).order_by(Ticket.id).with_for_update())).all()
    sprint.closed_total = len(tickets)
    sprint.closed_completed = sum(ticket.status == TicketStatus.COMPLETED for ticket in tickets)
    for ticket in tickets:
        if ticket.status != TicketStatus.COMPLETED:
            ticket.sprint_id = None
    sprint.status = "FINISHED"
    sprint.finished_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sprint)
    return (await responses(db, [sprint]))[0]


@router.get("/{sprint_id}/tickets", response_model=TicketSearchResponse)
async def sprint_tickets(sprint_id: UUID, available: bool = False, q: str = Query("", max_length=200),
                         skip: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
                         user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sprint = await db.get(Sprint, sprint_id)
    if sprint is None:
        raise HTTPException(404, "Sprint no encontrado")
    query = select(Ticket)
    if available:
        query = query.join(Epic).where(Epic.application_id == sprint.application_id,
            Ticket.sprint_id.is_(None), Ticket.ticket_type == TicketType.DEVELOPMENT,
            Ticket.status != TicketStatus.COMPLETED)
    else:
        query = query.where(Ticket.sprint_id == sprint_id)
    if q.strip():
        value = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Ticket.title.ilike(f"%{value}%", escape="\\"))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    items = (await db.scalars(query.options(
        selectinload(Ticket.assignee).selectinload(User.role),
        selectinload(Ticket.epic).selectinload(Epic.application),
        selectinload(Ticket.subtasks), selectinload(Ticket.linked_ticket).selectinload(Ticket.epic),
    ).order_by(Ticket.created_at, Ticket.id).offset(skip).limit(limit))).all()
    return {"items": [TicketResponse.model_validate(ticket) for ticket in items], "total": total, "skip": skip, "limit": limit}


@router.put("/{sprint_id}/tickets/{ticket_id}", status_code=204)
async def add_ticket(sprint_id: UUID, ticket_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_admin_or_leader(user)
    sprint = await lock_sprint(db, sprint_id)
    if sprint.status == "FINISHED":
        raise HTTPException(409, "El sprint finalizado no admite cambios")
    ticket = await db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
    if ticket is None:
        raise HTTPException(404, "Ticket no encontrado")
    application_id = await db.scalar(select(Epic.application_id).where(Epic.id == ticket.epic_id))
    if application_id != sprint.application_id or ticket.ticket_type != TicketType.DEVELOPMENT:
        raise HTTPException(422, "El ticket debe ser de desarrollo y pertenecer a la misma aplicación")
    if ticket.status == TicketStatus.COMPLETED:
        raise HTTPException(409, "No se puede planificar un ticket ya completado")
    if ticket.sprint_id is not None and ticket.sprint_id != sprint_id:
        raise HTTPException(409, "El ticket ya pertenece a otro sprint; retíralo primero")
    ticket.sprint_id = sprint_id
    await db.commit()


@router.delete("/{sprint_id}/tickets/{ticket_id}", status_code=204)
async def remove_ticket(sprint_id: UUID, ticket_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    require_admin_or_leader(user)
    sprint = await lock_sprint(db, sprint_id)
    if sprint.status == "FINISHED":
        raise HTTPException(409, "El sprint finalizado no admite cambios")
    ticket = await db.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
    if ticket is None or ticket.sprint_id != sprint_id:
        raise HTTPException(404, "El ticket no pertenece al sprint")
    ticket.sprint_id = None
    await db.commit()
