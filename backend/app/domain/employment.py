"""Employment type, FTE and status rules."""

from datetime import date
from decimal import Decimal
from enum import StrEnum

from app.domain.errors import InvalidFteError

FULL_FTE = Decimal(1)


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACTOR = "contractor"


class EmploymentStatus(StrEnum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"


def validate_fte(employment_type: EmploymentType, fte: Decimal) -> None:
    """Full-time is exactly 1.0; part-time is strictly between 0 and 1; contractors up to 1."""
    valid = {
        EmploymentType.FULL_TIME: fte == FULL_FTE,
        EmploymentType.PART_TIME: Decimal(0) < fte < FULL_FTE,
        EmploymentType.CONTRACTOR: Decimal(0) < fte <= FULL_FTE,
    }[employment_type]
    if not valid:
        raise InvalidFteError(
            "FTE doesn't fit the employment type: full-time is 1.0, part-time is between "
            "0 and 1, and contractors are above 0 and at most 1.",
            employment_type=employment_type,
            fte=str(fte),
        )


def status_on(
    status: EmploymentStatus, termination_date: date | None, as_of: date
) -> EmploymentStatus:
    """Employment status on a date. The termination date is the last day worked.

    Terminating someone records the date; they stay active (or on leave) until
    that day and count as terminated from the day after, worked out at read time.
    """
    if termination_date is not None and as_of > termination_date:
        return EmploymentStatus.TERMINATED
    return status


def is_current_employee(status: EmploymentStatus) -> bool:
    """Counted in headcount and current cost. People on leave are still employed."""
    return status is not EmploymentStatus.TERMINATED
