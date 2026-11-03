"""NEW-03: persistencia, autorización y filtros contra PostgreSQL real."""
from datetime import datetime, timedelta, timezone
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_etiquetas_persisten_y_se_normalizan(client, leader_headers, dev_headers, ticket):
    url = f"/api/tickets/{ticket['id']}"
    response = await client.put(url, headers=dev_headers, json={"labels": ["  Interfaz ", "INTERFAZ", "Revisión   final"]})
    assert response.status_code == 200, response.text
    assert response.json()["labels"] == ["interfaz", "revisión final"]
    assert (await client.get(url, headers=leader_headers)).json()["labels"] == ["interfaz", "revisión final"]
    await client.put(url, headers=leader_headers, json={"title": "Título editado"})
    assert (await client.get(url, headers=dev_headers)).json()["labels"] == ["interfaz", "revisión final"]
    response = await client.put(url, headers=dev_headers, json={"labels": []})
    assert response.json()["labels"] == []


async def test_etiquetas_respetan_permisos(client, dev2_headers, dev_headers, ticket):
    url = f"/api/tickets/{ticket['id']}"
    assert (await client.put(url, headers=dev2_headers, json={"labels": ["ajena"]})).status_code == 403
    assert (await client.get(url, headers=dev_headers)).json()["labels"] == []


@pytest.mark.parametrize("labels", [None, [""], [" "], ["x" * 41], [str(i) for i in range(11)], ["no\u200bvisible"]])
async def test_etiquetas_invalidas(client, dev_headers, ticket, labels):
    response = await client.put(f"/api/tickets/{ticket['id']}", headers=dev_headers, json={"labels": labels})
    assert response.status_code == 422


async def test_busqueda_combinada_y_paginacion(client, leader_headers, dev_headers, dev_id, epic, application):
    for title, labels in [("Revisión login", ["web", "urgente"]), ("Revisión login dos", ["web"]), ("Revisión login tres", ["web", "urgente"])]:
        response = await client.post("/api/tickets/", headers=leader_headers, json={
            "epic_id": epic["id"], "title": title, "description": "Formulario de acceso",
            "assignee_id": dev_id, "priority": "HIGH", "labels": labels,
        })
        assert response.status_code == 201, response.text
    params = [("q", "ACCESO"), ("labels", " WEB "), ("labels", "urgente"),
              ("status_filter", "TODO"), ("priority", "HIGH"), ("application_id", application["id"]),
              ("assignee_id", dev_id), ("ticket_type", "DEVELOPMENT"), ("limit", "1")]
    first = await client.get("/api/tickets/search", params=params, headers=dev_headers)
    assert first.status_code == 200, first.text
    assert first.json()["total"] == 2
    second = await client.get("/api/tickets/search", params=params + [("skip", "1")], headers=dev_headers)
    assert len(first.json()["items"]) == len(second.json()["items"]) == 1
    assert first.json()["items"][0]["id"] != second.json()["items"][0]["id"]
    empty = await client.get("/api/tickets/search", params=params + [("skip", "2")], headers=dev_headers)
    assert empty.json()["items"] == []
    assert empty.json()["total"] == 2


async def test_texto_literal_identificador_y_fechas(client, leader_headers, dev_headers, ticket):
    url = f"/api/tickets/{ticket['id']}"
    await client.put(url, headers=leader_headers, json={"description": "avance 50%_final"})
    for text, total in [("50%_", 1), ("inexistente", 0), (ticket["id"], 1), ("50_", 0)]:
        response = await client.get("/api/tickets/search", headers=dev_headers, params={"q": text})
        assert response.status_code == 200, response.text
        assert response.json()["total"] == total
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    response = await client.get("/api/tickets/search", headers=dev_headers, params={"created_from": future})
    assert response.json()["total"] == 0
    response = await client.get("/api/tickets/search", headers=dev_headers, params={"created_to": future})
    assert response.json()["total"] == 1
    response = await client.get("/api/tickets/search", headers=dev_headers, params={"unassigned": "true"})
    assert response.json()["total"] == 0


@pytest.mark.parametrize("params", [
    {"priority": "incorrecta"}, {"status_filter": "incorrecto"}, {"limit": 101},
    {"skip": -1}, {"labels": "x" * 41}, {"created_from": "2026-11-01T00:00:00"},
    {"created_from": "2026-11-03T00:00:00Z", "created_to": "2026-11-01T00:00:00Z"},
])
async def test_busqueda_valida_filtros(client, dev_headers, params):
    assert (await client.get("/api/tickets/search", headers=dev_headers, params=params)).status_code == 422


async def test_busqueda_requiere_sesion(client):
    assert (await client.get("/api/tickets/search")).status_code == 401
