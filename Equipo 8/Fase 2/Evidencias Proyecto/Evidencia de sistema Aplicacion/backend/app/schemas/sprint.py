"""Validaciones y contratos de planificación de sprints."""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SprintPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    goal: str = Field(min_length=1, max_length=2000)
    start_date: date
    end_date: date

    @field_validator("name", "goal")
    @classmethod
    def nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre y el objetivo no pueden estar vacíos")
        return value

    @model_validator(mode="after")
    def valid_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("La fecha de término debe ser posterior o igual al inicio")
        return self


class SprintCreate(SprintPlan):
    application_id: UUID


class SprintResponse(SprintPlan):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    application_id: UUID
    status: Literal["PLANNED", "ACTIVE", "FINISHED"]
    started_at: datetime | None
    finished_at: datetime | None
    total_tickets: int
    completed_tickets: int
    progress: float
    released_tickets: int = 0


class SprintPage(BaseModel):
    items: list[SprintResponse]
    total: int
    skip: int
    limit: int
