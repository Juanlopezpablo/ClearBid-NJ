"""NEW-09: reintentos idempotentes, cuentas y conflictos en PostgreSQL real."""
import asyncio
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_reintento_concurrente_no_duplica(client, dev_headers, dev_id, ticket):
    path = f"/api/tickets/{ticket['id']}/comments/offline"
    payload = {"client_id": str(uuid4()), "author_id": dev_id, "body": "Comentario escrito sin conexión"}
    first, retry = await asyncio.gather(client.post(path, headers=dev_headers, json=payload), client.post(path, headers=dev_headers, json=payload))
    assert first.status_code == retry.status_code == 201, (first.text, retry.text)
    assert first.json()["id"] == retry.json()["id"]
    comments = await client.get(f"/api/tickets/{ticket['id']}/comments", headers=dev_headers)
    assert len(comments.json()) == 1
    changed = await client.post(path, headers=dev_headers, json={**payload, "body": "Contenido diferente"})
    assert changed.status_code == 409


async def test_pendiente_de_otra_cuenta_se_rechaza(client, dev_headers, dev_id, dev2_headers, ticket):
    response = await client.post(f"/api/tickets/{ticket['id']}/comments/offline", headers=dev2_headers,
        json={"client_id": str(uuid4()), "author_id": dev_id, "body": "No debe enviarse como otra persona"})
    assert response.status_code == 403
    assert (await client.get(f"/api/tickets/{ticket['id']}/comments", headers=dev_headers)).json() == []


async def test_comentario_eliminado_no_resucita(client, dev_headers, dev_id, admin_headers, ticket):
    path = f"/api/tickets/{ticket['id']}/comments/offline"
    payload = {"client_id": str(uuid4()), "author_id": dev_id, "body": "Comentario que luego se retira"}
    first = await client.post(path, headers=dev_headers, json=payload)
    assert first.status_code == 201, first.text
    assert (await client.delete(f"/api/tickets/{ticket['id']}/comments/{first.json()['id']}", headers=admin_headers)).status_code == 204
    assert (await client.post(path, headers=dev_headers, json=payload)).status_code == 410


async def test_ticket_eliminado_y_mencion_invalida(client, dev_headers, dev_id, admin_headers, ticket):
    path = f"/api/tickets/{ticket['id']}/comments/offline"
    payload = {"client_id": str(uuid4()), "author_id": dev_id, "body": f"Hola @[Usuario eliminado]({uuid4()})"}
    assert (await client.post(path, headers=dev_headers, json=payload)).status_code == 422
    payload["body"] = "Comentario pendiente para ticket eliminado"
    assert (await client.delete(f"/api/tickets/{ticket['id']}", headers=admin_headers)).status_code == 204
    assert (await client.post(path, headers=dev_headers, json=payload)).status_code == 404


async def test_sin_sesion_no_sincroniza(client, dev_id, ticket):
    response = await client.post(f"/api/tickets/{ticket['id']}/comments/offline",
        json={"client_id": str(uuid4()), "author_id": dev_id, "body": "Necesita autenticar"})
    assert response.status_code == 401
