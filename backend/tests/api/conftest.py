"""API tests share one in-memory database with the app, holding the integration reference data."""

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.domain.components import ComponentBasis, ComponentType, Frequency
from app.domain.employment import EmploymentType
from app.domain.versions import ChangeReason
from app.services.compensation import CompensationService
from app.services.employees import EmployeeService
from app.services.inputs import ComponentInput, RevisionRequest
from tests.integration.factories import Reference, hire_request, lakh, seed_reference


@pytest.fixture
def db(app: FastAPI) -> Iterator[Session]:
    with app.state.session_factory() as session:
        yield session


@pytest.fixture
def reference(db: Session) -> Reference:
    return seed_reference(db)


HOUSING = ComponentInput(
    ComponentType.ALLOWANCE,
    ComponentBasis.FIXED_AMOUNT,
    Frequency.MONTHLY,
    "Housing allowance",
    amount_minor=lakh(30_000),
)
MEAL = ComponentInput(
    ComponentType.ALLOWANCE,
    ComponentBasis.FIXED_AMOUNT,
    Frequency.MONTHLY,
    "Meal allowance",
    amount_minor=lakh(2_200),
)
SIGN_ON = ComponentInput(
    ComponentType.ONE_TIME,
    ComponentBasis.FIXED_AMOUNT,
    Frequency.ONCE,
    "Sign-on bonus",
    amount_minor=lakh(1_50_000),
    payout_date=date(2022, 3, 14),
)
BONUS_10 = ComponentInput(
    ComponentType.BONUS,
    ComponentBasis.PERCENT_OF_BASE,
    Frequency.ANNUAL,
    "Annual bonus",
    percent=Decimal("10"),
)


def money(amount_minor: int, currency: str = "INR") -> dict[str, Any]:
    return {"amount_minor": amount_minor, "currency": currency}


@pytest.fixture
def company(db: Session, reference: Reference) -> dict[str, int]:
    """Ravi as on the profile design, plus three colleagues."""
    hire = EmployeeService(db).hire
    revise = CompensationService(db).revise

    ravi = hire(
        hire_request(
            reference,
            role_id=reference.se_l3_id,
            components=(HOUSING, MEAL, SIGN_ON),
            base_annual_minor=lakh(22_00_000),
        )
    )
    revise(
        ravi,
        RevisionRequest(
            date(2025, 4, 1),
            ChangeReason.MERIT,
            lakh(24_00_000),
            components=(HOUSING, MEAL, BONUS_10),
        ),
    )
    neha = hire(
        hire_request(
            reference,
            employee_code="EMP-03345",
            name="Neha Gupta",
            email="neha@acme.example",
            base_annual_minor=lakh(21_10_000),
        )
    )
    hannah = hire(
        hire_request(
            reference,
            employee_code="EMP-05874",
            name="Hannah Clarke",
            email="hannah@acme.example",
            country_code="DE",
            base_annual_minor=75_000_00,
        )
    )
    rahul = hire(
        hire_request(
            reference,
            employee_code="EMP-05567",
            name="Rahul Das",
            email="rahul@acme.example",
            employment_type=EmploymentType.CONTRACTOR,
            base_annual_minor=lakh(28_00_000),
            components=(),
        )
    )
    return {"ravi": ravi, "neha": neha, "hannah": hannah, "rahul": rahul}
