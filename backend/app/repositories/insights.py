"""Queries for insights that the directory query doesn't already answer."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.versions import ChangeReason
from app.models import CompensationVersion


@dataclass(frozen=True, slots=True)
class DueChange:
    version_id: int
    employee_id: int
    effective_from: date
    reason: ChangeReason
    base_annual_minor: int
    currency: str


class InsightsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def changes_due(self, after: date, until: date) -> list[DueChange]:
        rows = self._session.execute(
            select(CompensationVersion)
            .where(
                CompensationVersion.effective_from > after,
                CompensationVersion.effective_from <= until,
            )
            .order_by(CompensationVersion.effective_from, CompensationVersion.id)
        ).scalars()
        return [
            DueChange(
                row.id,
                row.employee_id,
                row.effective_from,
                row.reason,
                row.base_annual_minor,
                row.currency,
            )
            for row in rows
        ]

    def recent_change_ids(self, limit: int) -> list[tuple[int, int]]:
        """(employee id, version id) of the latest recorded changes other than hires."""
        rows = self._session.execute(
            select(CompensationVersion.employee_id, CompensationVersion.id)
            .where(CompensationVersion.reason != ChangeReason.HIRE)
            .order_by(
                CompensationVersion.created_at.desc(),
                CompensationVersion.effective_from.desc(),
                CompensationVersion.id.desc(),
            )
            .limit(limit)
        )
        return [(employee_id, version_id) for employee_id, version_id in rows]
