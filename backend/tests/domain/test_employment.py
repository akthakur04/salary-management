from decimal import Decimal

import pytest

from app.domain.employment import (
    EmploymentStatus,
    EmploymentType,
    is_current_employee,
    validate_fte,
)
from app.domain.errors import InvalidFteError


def test_full_time_employee_works_full_fte() -> None:
    validate_fte(EmploymentType.FULL_TIME, Decimal("1"))


def test_full_time_employee_below_full_fte_is_rejected() -> None:
    with pytest.raises(InvalidFteError):
        validate_fte(EmploymentType.FULL_TIME, Decimal("0.8"))


@pytest.mark.parametrize("fte", ["0", "1", "1.2", "-0.5"])
def test_part_time_fte_must_be_between_zero_and_one(fte: str) -> None:
    with pytest.raises(InvalidFteError):
        validate_fte(EmploymentType.PART_TIME, Decimal(fte))


def test_part_time_employee_can_work_sixty_percent() -> None:
    validate_fte(EmploymentType.PART_TIME, Decimal("0.6"))


@pytest.mark.parametrize("fte", ["0", "1.5"])
def test_contractor_fte_must_be_above_zero_and_at_most_one(fte: str) -> None:
    with pytest.raises(InvalidFteError):
        validate_fte(EmploymentType.CONTRACTOR, Decimal(fte))


def test_terminated_employee_is_excluded_from_headcount_and_current_cost() -> None:
    assert not is_current_employee(EmploymentStatus.TERMINATED)


def test_employee_on_leave_is_counted_in_headcount_and_cost() -> None:
    assert is_current_employee(EmploymentStatus.ON_LEAVE)
    assert is_current_employee(EmploymentStatus.ACTIVE)
