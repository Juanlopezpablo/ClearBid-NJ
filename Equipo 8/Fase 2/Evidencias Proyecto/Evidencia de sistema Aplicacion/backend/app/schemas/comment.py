from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CommentWrite(BaseModel):
    body: str = Field(min_length=1, max_length=5000)

    @field_validator("body")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El comentario no puede estar vacío")
        return value


class CommentResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    author_id: UUID | None
    author_name: str
    body: str
    created_at: datetime
    updated_at: datetime


class MentionUser(BaseModel):
    id: UUID
    full_name: str

