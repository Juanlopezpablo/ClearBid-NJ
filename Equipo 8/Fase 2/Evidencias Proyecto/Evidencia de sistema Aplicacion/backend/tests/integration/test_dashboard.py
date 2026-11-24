"""APP-08: identidad, alcance, métricas y paginación en PostgreSQL real."""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import pytest
from app.database import get_session_maker
from app.models import Epic, Incident, Sprint, Team, Ticket, TicketStatus, TicketType, User
pytestmark = pytest.mark.asyncio(loop_scope="session")

async def summary(client, headers, **params):
    response = await client.get("/api/dashboard", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()

async def test_inicio_personal_no_expone_tickets_ajenos(client, admin_headers, leader_headers, dev_headers, dev2_headers, dev2_id, ticket, epic):
    other = await client.post("/api/tickets/", headers=leader_headers, json={"epic_id": epic["id"], "title": "Ticket de otra cuenta", "assignee_id": dev2_id})
    assert other.status_code == 201
    for headers, expected, role in [(admin_headers, 2, "ADMIN"), (leader_headers, 2, "TEAM_LEADER"), (dev_headers, 1, "DEVELOPER"), (dev2_headers, 1, "DEVELOPER")]:
        data = await summary(client, headers)
        assert data["metrics"]["pending"] == expected
        assert data["role"] == role
    data = await summary(client, dev_headers, role="ADMIN", assignee_id=dev2_id)
    assert [item["id"] for item in data["tickets"]["items"]] == [ticket["id"]]
    assert data["teams"] == []
    assert data["scope"] == "personal"

async def test_equipo_filtra_epicas_y_no_inventa_incidencias(client, leader_headers, dev_headers, dev_id, dev2_id, application, epic, ticket):
    now = datetime.now(timezone.utc)
    async with get_session_maker()() as db:
        team_a, team_b = Team(name="Equipo A"), Team(name="Equipo B")
        db.add_all([team_a, team_b]); await db.flush()
        own_epic = await db.get(Epic, UUID(epic["id"]))
        own_epic.team_id = team_a.id
        other_epic = Epic(title="Otra epica misma aplicacion", application_id=UUID(application["id"]), team_id=team_b.id)
        db.add(other_epic); await db.flush()
        other = Ticket(title="Fuera del equipo", epic_id=other_epic.id, assignee_id=UUID(dev2_id), status=TicketStatus.COMPLETED)
        sprint = Sprint(application_id=UUID(application["id"]), name="Sprint activo", goal="Objetivo", start_date=now.date(), end_date=(now+timedelta(days=7)).date(), status="ACTIVE")
        db.add_all([other, sprint]); await db.flush()
        own = await db.get(Ticket, UUID(ticket["id"]))
        own.sprint_id = other.sprint_id = sprint.id
        db.add(Incident(title="Incidencia de aplicacion compartida", application_id=UUID(application["id"]), assigned_to_id=UUID(dev_id)))
        await db.commit()
        team_id = str(team_a.id)
    general = await summary(client, leader_headers)
    assert general["incidents"]["total"] == 1
    assert general["active_sprints"]["items"][0]["progress"] == 50
    team = await summary(client, leader_headers, team_id=team_id)
    assert team["scope"] == "team"
    assert team["tickets"]["total"] == 1
    assert team["active_sprints"]["items"][0]["total_tickets"] == 1
    assert team["active_sprints"]["items"][0]["progress"] == 0
    assert team["incidents"] == {"available": False, "total": None, "items": []}
    personal = await summary(client, dev_headers)
    assert personal["active_sprints"]["items"][0]["total_tickets"] == 1
    assert personal["incidents"]["total"] == 1
    assert (await client.get("/api/dashboard", headers=dev_headers, params={"team_id": team_id})).status_code == 403

async def test_estados_soporte_vencimientos_y_paginacion(client, dev_headers, dev_id, epic, ticket):
    now = datetime.now(timezone.utc)
    async with get_session_maker()() as db:
        own = await db.get(Ticket, UUID(ticket["id"]))
        own.status = TicketStatus.BLOCKED_QUESTION
        own.due_date = now - timedelta(days=1)
        db.add_all([
            Ticket(title="Soporte en investigacion", assignee_id=UUID(dev_id), ticket_type=TicketType.SUPPORT, status=TicketStatus.INVESTIGATING, due_date=now+timedelta(days=2)),
            Ticket(title="Soporte resuelto vencido", assignee_id=UUID(dev_id), ticket_type=TicketType.SUPPORT, status=TicketStatus.RESOLVED, due_date=now-timedelta(days=2)),
            Ticket(title="Sin asignar", epic_id=UUID(epic["id"]), due_date=now-timedelta(days=1)),
        ])
        await db.commit()
    data = await summary(client, dev_headers, limit=1)
    assert data["metrics"] == {"pending": 2, "in_progress": 1, "blocked": 1, "overdue": 1, "upcoming": 1}
    assert data["tickets"]["items"][0]["id"] == ticket["id"]
    second = await summary(client, dev_headers, limit=1, skip=1)
    assert second["tickets"]["total"] == 2
    assert second["tickets"]["items"][0]["ticket_type"] == "SUPPORT"
    due = await summary(client, dev_headers, focus="upcoming")
    assert due["tickets"]["total"] == 1
    assert due["tickets"]["items"][0]["title"] == "Soporte en investigacion"

async def test_vacio_autorizacion_y_parametros(client, dev_headers, leader_headers):
    assert (await client.get("/api/dashboard")).status_code == 401
    empty = await summary(client, dev_headers)
    assert all(value == 0 for value in empty["metrics"].values())
    assert empty["active_sprints"]["total"] == 0
    assert empty["incidents"]["total"] == 0
    assert (await client.get("/api/dashboard", headers=leader_headers, params={"team_id": str(uuid4())})).status_code == 404
    for params in ({"focus": "todos"}, {"skip": -1}, {"limit": 100}, {"team_id": "invalido"}):
        assert (await client.get("/api/dashboard", headers=dev_headers, params=params)).status_code == 422

async def test_usuario_inactivo_no_consulta_inicio(client, dev_headers, dev_id):
    async with get_session_maker()() as db:
        user = await db.get(User, UUID(dev_id))
        user.is_active = False
        await db.commit()
    response = await client.get("/api/dashboard", headers=dev_headers)
    assert response.status_code in (401, 403)
