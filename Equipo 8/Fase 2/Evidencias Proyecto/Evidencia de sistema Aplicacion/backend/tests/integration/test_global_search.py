"""NEW-13: búsqueda real, extracción, paginación y acceso autenticado."""
import pytest
from tests.integration.test_documents import _subir
pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_global_busca_contenido_y_nombre(client, dev_headers, ticket):
    upload = await _subir(client, dev_headers, "manual-unificado.txt", b"Antes del texto: sincronizacion extraordinaria y evidencia", ticket_id=ticket["id"])
    assert upload.status_code == 201, upload.text
    for query in ("extraordinaria", "manual-unificado"):
        result = await client.get("/api/search", headers=dev_headers, params={"q": query, "kind": "document"})
        assert result.status_code == 200, result.text
        assert result.json()["total"] == 1
        item = result.json()["items"][0]
        assert item["id"] == upload.json()["id"]
        assert "extraordinaria" in item["snippet"]
        assert "file_path" not in item
    await client.delete(f"/api/documents/{upload.json()['id']}", headers=dev_headers)
    assert (await client.get("/api/search", headers=dev_headers, params={"q": "extraordinaria"})).json()["total"] == 0

async def test_global_literal_y_paginacion(client, leader_headers, dev_headers, ticket):
    await client.put(f"/api/tickets/{ticket['id']}", headers=leader_headers, json={"description": "unificado 50%_final"})
    for query, count in [("50%_", 1), ("50_", 0), (ticket["id"], 1)]:
        result = await client.get("/api/search", headers=dev_headers, params={"q": query, "kind": "ticket", "limit": 1})
        assert result.status_code == 200, result.text
        assert result.json()["total"] == count
    result = await client.get("/api/search", headers=dev_headers, params={"q": "unificado", "skip": 1, "limit": 1})
    assert result.json()["total"] == 1 and result.json()["items"] == []

async def test_global_auth_y_validacion(client, dev_headers):
    assert (await client.get("/api/search", params={"q": "manual"})).status_code == 401
    for params in ({"q": "x"}, {"q": "texto", "kind": "users"}, {"q": "texto", "skip": -1}):
        assert (await client.get("/api/search", headers=dev_headers, params=params)).status_code == 422

async def test_global_imagen_por_nombre(client, dev_headers, ticket):
    upload = await _subir(client, dev_headers, "captura-buscable.png", b"imagen", "image/png", ticket_id=ticket["id"])
    assert upload.status_code == 201
    result = await client.get("/api/search", headers=dev_headers, params={"q": "captura-buscable", "kind": "document"})
    assert result.json()["total"] == 1
    assert result.json()["items"][0]["snippet"] == ""
