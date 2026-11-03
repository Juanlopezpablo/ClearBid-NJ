"""NEW-05: planificación real con permisos, concurrencia y cierre atómico."""
import asyncio
from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.database import get_session_maker
from app.models import Ticket, TicketStatus, TicketType

pytestmark = pytest.mark.asyncio(loop_scope="session")
PLAN = {"name": "Iteración 1", "goal": "Entregar el flujo de acceso", "start_date": "2026-11-03", "end_date": "2026-11-17"}


async def create(client, headers, application, **changes):
    response = await client.post("/api/sprints", headers=headers, json={**PLAN, "application_id": application["id"], **changes})
    assert response.status_code == 201, response.text
    return response.json()


async def attach(client, headers, sprint, ticket):
    response = await client.put(f"/api/sprints/{sprint['id']}/tickets/{ticket['id']}", headers=headers)
    assert response.status_code == 204, response.text


async def test_planificacion_y_consulta_developer(client, leader_headers, dev_headers, application, ticket):
    sprint = await create(client, leader_headers, application)
    assert sprint["status"] == "PLANNED"
    assert sprint["progress"] == 0
    await attach(client, leader_headers, sprint, ticket)
    result = await client.get(f"/api/sprints/{sprint['id']}", headers=dev_headers)
    assert result.json()["total_tickets"] == 1
    items = await client.get(f"/api/sprints/{sprint['id']}/tickets", headers=dev_headers)
    assert items.status_code == 200, items.text
    assert items.json()["items"][0]["id"] == ticket["id"]
    assert items.json()["items"][0]["sprint_id"] == sprint["id"]
    page = await client.get("/api/sprints", headers=dev_headers, params={"application_id": application["id"]})
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["total_tickets"] == 1
    updated = await client.put(f"/api/sprints/{sprint['id']}", headers=leader_headers, json={**PLAN, "name": "Nombre corregido"})
    assert updated.json()["name"] == "Nombre corregido"


async def test_cierre_libera_pendientes_y_conserva_resumen(client, admin_headers, leader_headers, dev_headers, application, epic, ticket, dev_id):
    sprint = await create(client, admin_headers, application)
    second = (await client.post("/api/tickets/", headers=leader_headers, json={"epic_id": epic["id"], "title": "Pendiente", "assignee_id": dev_id})).json()
    await attach(client, leader_headers, sprint, ticket)
    await attach(client, leader_headers, sprint, second)
    started = await client.post(f"/api/sprints/{sprint['id']}/start", headers=leader_headers)
    assert started.json()["status"] == "ACTIVE"
    async with get_session_maker()() as db:
        done = await db.get(Ticket, UUID(ticket["id"]))
        done.status = TicketStatus.COMPLETED
        done.completed_at = datetime.now(timezone.utc)
        pending = await db.get(Ticket, UUID(second["id"]))
        pending.status = TicketStatus.BLOCKED
        pending.block_reason = "Dependencia externa"
        await db.commit()
    assert (await client.get(f"/api/sprints/{sprint['id']}", headers=dev_headers)).json()["progress"] == 50
    closed = await client.post(f"/api/sprints/{sprint['id']}/finish", headers=admin_headers)
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "FINISHED"
    assert closed.json()["total_tickets"] == 2
    assert closed.json()["completed_tickets"] == closed.json()["released_tickets"] == 1
    pending = (await client.get(f"/api/tickets/{second['id']}", headers=dev_headers)).json()
    assert pending["sprint_id"] is None
    assert pending["assignee_id"] == dev_id
    assert pending["status"] == "BLOCKED"
    assert pending["block_reason"] == "Dependencia externa"
    done = (await client.get(f"/api/tickets/{ticket['id']}", headers=dev_headers)).json()
    assert done["sprint_id"] == sprint["id"]
    next_sprint = await create(client, admin_headers, application, name="Iteración 2")
    await attach(client, leader_headers, next_sprint, second)
    old = (await client.get(f"/api/sprints/{sprint['id']}", headers=dev_headers)).json()
    assert old["total_tickets"] == 2 and old["progress"] == 50
    for path in ("start", "finish"):
        assert (await client.post(f"/api/sprints/{sprint['id']}/{path}", headers=admin_headers)).status_code == 409
    assert (await client.put(f"/api/sprints/{sprint['id']}/tickets/{second['id']}", headers=admin_headers)).status_code == 409
    assert (await client.delete(f"/api/sprints/{sprint['id']}/tickets/{ticket['id']}", headers=admin_headers)).status_code == 409


async def test_un_sprint_activo_con_solicitudes_simultaneas(client, leader_headers, application, epic, ticket):
    one = await create(client, leader_headers, application)
    two = await create(client, leader_headers, application, name="Iteración 2")
    another = (await client.post("/api/tickets/", headers=leader_headers, json={"epic_id": epic["id"], "title": "Otro trabajo"})).json()
    await attach(client, leader_headers, one, ticket)
    await attach(client, leader_headers, two, another)
    results = await asyncio.gather(*[client.post(f"/api/sprints/{s['id']}/start", headers=leader_headers) for s in [one, two]])
    assert sorted(response.status_code for response in results) == [200, 409]
    page = (await client.get("/api/sprints", headers=leader_headers, params={"application_id": application["id"]})).json()
    assert sum(s["status"] == "ACTIVE" for s in page["items"]) == 1


async def test_developer_no_administra_sprints(client, leader_headers, dev_headers, application, ticket):
    sprint = await create(client, leader_headers, application)
    assert (await client.post("/api/sprints", headers=dev_headers, json={**PLAN, "application_id": application["id"]})).status_code == 403
    assert (await client.put(f"/api/sprints/{sprint['id']}", headers=dev_headers, json=PLAN)).status_code == 403
    for action in ["start", "finish"]:
        assert (await client.post(f"/api/sprints/{sprint['id']}/{action}", headers=dev_headers)).status_code == 403
    path = f"/api/sprints/{sprint['id']}/tickets/{ticket['id']}"
    assert (await client.put(path, headers=dev_headers)).status_code == 403
    assert (await client.delete(path, headers=dev_headers)).status_code == 403


async def test_ticket_no_puede_estar_en_dos_sprints(client, leader_headers, application, ticket):
    one = await create(client, leader_headers, application)
    two = await create(client, leader_headers, application, name="Otro sprint")
    await attach(client, leader_headers, one, ticket)
    response = await client.put(f"/api/sprints/{two['id']}/tickets/{ticket['id']}", headers=leader_headers)
    assert response.status_code == 409
    removed = await client.delete(f"/api/sprints/{one['id']}/tickets/{ticket['id']}", headers=leader_headers)
    assert removed.status_code == 204
    await attach(client, leader_headers, two, ticket)


async def test_rechaza_soporte_y_otras_aplicaciones(client, leader_headers, admin_headers, application, ticket):
    other_app = (await client.post("/api/applications/", headers=admin_headers, json={"name": "Otra aplicación"})).json()
    other = await create(client, leader_headers, other_app)
    path = f"/api/sprints/{other['id']}/tickets/{ticket['id']}"
    assert (await client.put(path, headers=leader_headers)).status_code == 422
    own = await create(client, leader_headers, application)
    async with get_session_maker()() as db:
        stored = await db.get(Ticket, UUID(ticket["id"]))
        stored.ticket_type = TicketType.SUPPORT
        await db.commit()
    assert (await client.put(f"/api/sprints/{own['id']}/tickets/{ticket['id']}", headers=leader_headers)).status_code == 422


async def test_backlog_no_depende_del_responsable(client, leader_headers, dev_headers, application, ticket):
    sprint = await create(client, leader_headers, application)
    path = f"/api/sprints/{sprint['id']}/tickets"
    response = await client.get(path, headers=dev_headers, params={"available": "true", "q": "PRUEBA", "limit": 1})
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == ticket["id"]
    await attach(client, leader_headers, sprint, ticket)
    assert (await client.get(path, headers=dev_headers, params={"available": "true"})).json()["total"] == 0


@pytest.mark.parametrize("changes", [{"name": " "}, {"goal": " "}, {"end_date": "2026-11-01"}, {"status": "ACTIVE"}, {"start_date": "incorrecta"}])
async def test_valida_plan(client, leader_headers, application, changes):
    response = await client.post("/api/sprints", headers=leader_headers, json={**PLAN, "application_id": application["id"], **changes})
    assert response.status_code == 422


async def test_transiciones_y_plan_activo(client, leader_headers, application, ticket):
    sprint = await create(client, leader_headers, application)
    base = f"/api/sprints/{sprint['id']}"
    assert (await client.post(base + "/start", headers=leader_headers)).status_code == 409
    assert (await client.post(base + "/finish", headers=leader_headers)).status_code == 409
    await attach(client, leader_headers, sprint, ticket)
    assert (await client.post(base + "/start", headers=leader_headers)).status_code == 200
    assert (await client.put(base, headers=leader_headers, json=PLAN)).status_code == 409
    assert (await client.post(base + "/start", headers=leader_headers)).status_code == 409


async def test_requiere_sesion(client, application):
    assert (await client.get("/api/sprints", params={"application_id": application["id"]})).status_code == 401
