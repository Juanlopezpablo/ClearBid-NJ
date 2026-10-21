"""HTTP + SQLite real: permisos, persistencia y menciones de NEW-01.

La entrega Redis se sustituye por un espía; las notificaciones se guardan de verdad.
"""
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models import Notification, Role, User
from app.routers import comments

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def context(db_session, sample_ticket, sample_user, monkeypatch):
    roles = {}
    users = {}
    for name in ("ADMIN", "TEAM_LEADER", "DEVELOPER"):
        role = (await db_session.scalars(select(Role).where(Role.name == name))).first()
        if role is None:
            role = Role(name=name)
            db_session.add(role)
            await db_session.flush()
        roles[name] = role
        user = User(
            full_name=name, email=f"{name.lower()}@example.com",
            hashed_password="unused", role=role, is_active=True,
        )
        db_session.add(user)
        users[name] = user
    inactive = User(
        full_name="Inactive", email="inactive@example.com",
        hashed_password="unused", role=roles["DEVELOPER"], is_active=False,
    )
    db_session.add(inactive)
    await db_session.commit()
    actor = [users["DEVELOPER"]]
    app = FastAPI()
    app.include_router(comments.router)

    async def session():
        yield db_session

    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_current_user] = lambda: actor[0]
    publish = AsyncMock(return_value=False)
    monkeypatch.setattr(comments, "publish_notification", publish)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, actor, users, inactive, sample_ticket, publish, app


@pytest.mark.parametrize("role", ["ADMIN", "TEAM_LEADER", "DEVELOPER"])
async def test_each_role_can_comment_and_edit_own(context, role):
    client, actor, users, _, ticket, _, _ = context
    actor[0] = users[role]
    url = f"/api/tickets/{ticket.id}/comments"
    created = await client.post(url, json={"body": "  Primer comentario  "})
    assert created.status_code == 201
    comment = created.json()
    assert comment["author_id"] == str(actor[0].id)
    assert comment["body"] == "Primer comentario"
    edited = await client.patch(f'{url}/{comment["id"]}', json={"body": "Editado"})
    assert edited.status_code == 200
    assert edited.json()["body"] == "Editado"
    assert (await client.get(url)).json()[0]["body"] == "Editado"


async def test_only_author_edits_only_admin_deletes(context):
    client, actor, users, _, ticket, _, _ = context
    url = f"/api/tickets/{ticket.id}/comments"
    comment = (await client.post(url, json={"body": "Propio"})).json()
    target = f'{url}/{comment["id"]}'
    assert (await client.delete(target)).status_code == 403
    actor[0] = users["TEAM_LEADER"]
    assert (await client.patch(target, json={"body": "Ajeno"})).status_code == 403
    assert (await client.delete(target)).status_code == 403
    actor[0] = users["ADMIN"]
    assert (await client.patch(target, json={"body": "Ajeno"})).status_code == 403
    assert (await client.delete(target)).status_code == 204
    assert (await client.get(url)).json() == []


async def test_mentions_persist_notify_once_and_only_new_on_edit(context, db_session):
    client, actor, users, _, ticket, publish, _ = context
    recipient = users["ADMIN"]
    token = f"@[Nombre falso]({recipient.id})"
    own = f"@[Yo]({actor[0].id})"
    url = f"/api/tickets/{ticket.id}/comments"
    result = await client.post(url, json={"body": f"Hola {token} {token} {own}"})
    assert result.status_code == 201
    comment = result.json()
    assert "@[ADMIN]" in comment["body"]
    assert "Nombre falso" not in comment["body"]
    notifications = (await db_session.scalars(select(Notification))).all()
    assert len(notifications) == 1
    assert notifications[0].user_id == recipient.id
    assert notifications[0].ticket_id == ticket.id
    publish.assert_awaited_once()
    # El espía simula Redis caído: el comentario y su notificación siguen guardados.
    target = f'{url}/{comment["id"]}'
    assert (await client.patch(target, json={"body": f"Otro texto {token}"})).status_code == 200
    assert publish.await_count == 1
    new_token = f'@[Líder]({users["TEAM_LEADER"].id})'
    assert (await client.patch(target, json={"body": f"{token} {new_token}"})).status_code == 200
    assert publish.await_count == 2
    assert await db_session.scalar(select(func.count()).select_from(Notification)) == 2


async def test_active_mentions_lookup_and_invalid_mentions(context, db_session):
    client, actor, users, inactive, ticket, publish, _ = context
    lookup = await client.get("/api/tickets/comment-mentions", params={"q": "ADMIN"})
    assert lookup.status_code == 200
    assert lookup.json() == [{"id": str(users["ADMIN"].id), "full_name": "ADMIN"}]
    assert all(set(row) == {"id", "full_name"} for row in lookup.json())
    assert (await client.get("/api/tickets/comment-mentions", params={"q": "Inactive"})).json() == []
    url = f"/api/tickets/{ticket.id}/comments"
    for user_id in (inactive.id, uuid4()):
        assert (await client.post(url, json={"body": f"Hola @[Usuario]({user_id})"})).status_code == 422
    assert (await client.get(url)).json() == []
    publish.assert_not_awaited()


@pytest.mark.parametrize("body", ["", " \n ", "x" * 5001])
async def test_invalid_body(context, body):
    client, _, _, _, ticket, _, _ = context
    assert (await client.post(f"/api/tickets/{ticket.id}/comments", json={"body": body})).status_code == 422


async def test_missing_ticket_comment_wrong_ticket_and_pagination(context):
    client, _, _, _, ticket, _, _ = context
    url = f"/api/tickets/{ticket.id}/comments"
    assert (await client.get(f"/api/tickets/{uuid4()}/comments")).status_code == 404
    assert (await client.post(f"/api/tickets/{uuid4()}/comments", json={"body": "Hola"})).status_code == 404
    first = (await client.post(url, json={"body": "Primero"})).json()
    await client.post(url, json={"body": "Segundo"})
    assert len((await client.get(url, params={"limit": 1})).json()) == 1
    assert (await client.get(url, params={"offset": 1})).json()[0]["body"] == "Segundo"
    assert (await client.get(url, params={"offset": -1})).status_code == 422
    assert (await client.patch(f'{url}/{uuid4()}', json={"body": "Hola"})).status_code == 404
    assert (await client.patch(
        f'/api/tickets/{uuid4()}/comments/{first["id"]}', json={"body": "Hola"}
    )).status_code == 404


async def test_authentication_and_inactive_user(context):
    client, actor, _, inactive, ticket, _, app = context
    url = f"/api/tickets/{ticket.id}/comments"
    actor[0] = inactive
    assert (await client.get(url)).status_code == 403
    assert (await client.post(url, json={"body": "Hola"})).status_code == 403
    assert (await client.get("/api/tickets/comment-mentions")).status_code == 403
    app.dependency_overrides.pop(get_current_user)
    assert (await client.get(url)).status_code in (401, 403)
    assert (await client.post(url, json={"body": "Hola"})).status_code in (401, 403)

