"""NEW-01: comentarios de tickets y menciones; notificaciones solo internas."""
import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models import Ticket, User
from app.models.comment import TicketComment
from app.schemas.comment import CommentResponse, CommentWrite, MentionUser
from app.services.notification_service import create_notification, publish_notification

router = APIRouter(prefix="/api/tickets", tags=["Comentarios"])
MENTION = re.compile(r"@\[([^\]\r\n]{1,255})\]\(([0-9a-fA-F-]{36})\)")


async def active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(403, "Usuario inactivo")
    return user


async def get_ticket(ticket_id: UUID, db: AsyncSession) -> Ticket:
    ticket = await db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "Ticket no encontrado")
    return ticket


async def get_comment(ticket_id: UUID, comment_id: UUID, db: AsyncSession) -> TicketComment:
    comment = await db.get(TicketComment, comment_id)
    if comment is None or comment.ticket_id != ticket_id:
        raise HTTPException(404, "Comentario no encontrado")
    return comment


async def validate_mentions(body: str, db: AsyncSession) -> tuple[str, list[str]]:
    """Resolver IDs en el servidor y guardar nombres canónicos, no nombres del cliente."""
    ids = set()
    for match in MENTION.finditer(body):
        try:
            ids.add(UUID(match[2]))
        except ValueError:
            raise HTTPException(422, "Mención inválida") from None
    if len(ids) > 20:
        raise HTTPException(422, "Máximo 20 usuarios mencionados por comentario")
    users = (await db.scalars(select(User).where(User.id.in_(ids), User.is_active.is_(True)))).all() if ids else []
    by_id = {str(user.id): user for user in users}
    if len(by_id) != len(ids):
        raise HTTPException(422, "Solo puedes mencionar usuarios activos")
    def canonical(match):
        user = by_id[str(UUID(match[2]))]
        name = re.sub(r"[\[\]\r\n]", " ", user.full_name)
        return f"@[{name}]({user.id})"
    canonical_body = MENTION.sub(canonical, body)
    if len(canonical_body) > 5000:
        raise HTTPException(422, "El comentario supera los 5000 caracteres")
    return canonical_body, sorted(by_id)


async def response(comment: TicketComment, db: AsyncSession) -> CommentResponse:
    author = await db.get(User, comment.author_id) if comment.author_id else None
    return CommentResponse(
        id=comment.id, ticket_id=comment.ticket_id, author_id=comment.author_id,
        author_name=author.full_name if author else "Usuario eliminado",
        body=comment.body, created_at=comment.created_at, updated_at=comment.updated_at,
    )


@router.get("/comment-mentions", response_model=list[MentionUser])
async def mention_users(
    q: str = Query("", max_length=100),
    current_user: User = Depends(active_user),
    db: AsyncSession = Depends(get_db),
):
    # Solo nombre e ID: disponible también para DEVELOPER sin exponer el directorio administrativo.
    query = select(User.id, User.full_name).where(User.is_active.is_(True))
    if q.strip():
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(User.full_name.ilike(f"%{escaped}%", escape="\\"))
    rows = (await db.execute(query.order_by(User.full_name, User.id).limit(20))).all()
    return [MentionUser(id=row.id, full_name=row.full_name) for row in rows]


@router.get("/{ticket_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    ticket_id: UUID, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(active_user), db: AsyncSession = Depends(get_db),
):
    await get_ticket(ticket_id, db)
    comments = (await db.scalars(select(TicketComment).where(
        TicketComment.ticket_id == ticket_id
    ).order_by(TicketComment.created_at, TicketComment.id).offset(offset).limit(limit))).all()
    return [await response(comment, db) for comment in comments]


async def save_comment(comment, data, ticket, user, db):
    body, mentions = await validate_mentions(data.body, db)
    new_mentions = set(mentions) - set(comment.mention_ids or [])
    comment.body = body
    comment.mention_ids = mentions
    comment.updated_at = datetime.now(timezone.utc) if comment.id else comment.created_at
    db.add(comment)
    notifications = []
    for user_id in sorted(new_mentions):
        if user_id == str(user.id):
            continue
        notifications.append(await create_notification(
            db, user_id=user_id, ticket_id=ticket.id,
            title="Te mencionaron en un comentario",
            message=f'{user.full_name} te mencionó en "{ticket.title}"',
            notification_type="SYSTEM",
        ))
    await db.commit()
    await db.refresh(comment)
    for notification in notifications:
        await publish_notification(notification)
    return await response(comment, db)


@router.post("/{ticket_id}/comments", response_model=CommentResponse, status_code=201)
async def create_comment(
    ticket_id: UUID, data: CommentWrite,
    current_user: User = Depends(active_user), db: AsyncSession = Depends(get_db),
):
    ticket = await get_ticket(ticket_id, db)
    now = datetime.now(timezone.utc)
    comment = TicketComment(
        ticket_id=ticket_id, author_id=current_user.id, mention_ids=[],
        created_at=now, updated_at=now,
    )
    return await save_comment(comment, data, ticket, current_user, db)


@router.patch("/{ticket_id}/comments/{comment_id}", response_model=CommentResponse)
async def edit_comment(
    ticket_id: UUID, comment_id: UUID, data: CommentWrite,
    current_user: User = Depends(active_user), db: AsyncSession = Depends(get_db),
):
    ticket = await get_ticket(ticket_id, db)
    comment = await get_comment(ticket_id, comment_id, db)
    if comment.author_id != current_user.id:
        raise HTTPException(403, "Solo puedes editar tus propios comentarios")
    return await save_comment(comment, data, ticket, current_user, db)


@router.delete("/{ticket_id}/comments/{comment_id}", status_code=204)
async def delete_comment(
    ticket_id: UUID, comment_id: UUID,
    current_user: User = Depends(require_role("ADMIN")), db: AsyncSession = Depends(get_db),
):
    if not current_user.is_active:
        raise HTTPException(403, "Usuario inactivo")
    await get_ticket(ticket_id, db)
    comment = await get_comment(ticket_id, comment_id, db)
    await db.delete(comment)
    await db.commit()
    return Response(status_code=204)

