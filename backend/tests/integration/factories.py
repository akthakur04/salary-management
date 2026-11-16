"""Fixture factories for database tests: a small, realistic slice of ACME's reference data."""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.domain.components import ComponentType
from app.domain.employment import EmploymentType
from app.models import Country, Department, FxRate, PayBand, Role, RoleDefaultComponent
from app.services.inputs import HireRequest

TODAY = date(2026, 11, 12)


@dataclass(frozen=True)
class Reference:
    engineering_id: int
    sales_id: int
    se_l3_id: int
    se_l4_id: int
    ae_l2_id: int


def lakh(rupees: int) -> int:
    """Rupees to paise, to keep Indian figures readable in tests."""
    return rupees * 100


def seed_reference(session: Session) -> Reference:
    session.add_all(
        [
            Country(code="IN", name="India", currency="INR"),
            Country(code="DE", name="Germany", currency="EUR"),
            Country(code="US", name="United States", currency="USD"),
            FxRate(
                rate_set="2026-ref", currency="INR", usd_per_unit=Decimal("0.012"), is_active=True
            ),
            FxRate(
                rate_set="2026-ref", currency="EUR", usd_per_unit=Decimal("1.08"), is_active=True
            ),
            FxRate(rate_set="2026-ref", currency="USD", usd_per_unit=Decimal("1"), is_active=True),
            FxRate(
                rate_set="2025-ref", currency="INR", usd_per_unit=Decimal("0.011"), is_active=False
            ),
        ]
    )
    engineering, sales = Department(name="Engineering"), Department(name="Sales")
    session.add_all([engineering, sales])
    session.flush()

    se_l3 = Role(
        department_id=engineering.id, family="Software Engineer", level=3, title="Software Engineer"
    )
    se_l4 = Role(
        department_id=engineering.id,
        family="Software Engineer",
        level=4,
        title="Senior Software Engineer",
    )
    ae_l2 = Role(
        department_id=sales.id, family="Account Executive", level=2, title="Account Executive"
    )
    session.add_all([se_l3, se_l4, ae_l2])
    session.flush()

    session.add_all(
        [
            RoleDefaultComponent(
                role_id=se_l3.id,
                type=ComponentType.BONUS,
                percent=Decimal("10"),
                label="Annual bonus",
            ),
            RoleDefaultComponent(
                role_id=se_l4.id,
                type=ComponentType.BONUS,
                percent=Decimal("15"),
                label="Annual bonus",
            ),
            RoleDefaultComponent(
                role_id=ae_l2.id,
                type=ComponentType.COMMISSION,
                percent=Decimal("40"),
                label="Sales commission",
            ),
            PayBand(
                role_id=se_l3.id,
                country_code="IN",
                min_minor=lakh(22_00_000),
                mid_minor=lakh(27_00_000),
                max_minor=lakh(32_00_000),
            ),
            PayBand(
                role_id=se_l4.id,
                country_code="IN",
                min_minor=lakh(28_00_000),
                mid_minor=lakh(33_00_000),
                max_minor=lakh(38_00_000),
            ),
            PayBand(
                role_id=se_l3.id,
                country_code="DE",
                min_minor=60_000_00,
                mid_minor=70_000_00,
                max_minor=80_000_00,
            ),
            PayBand(
                role_id=ae_l2.id,
                country_code="US",
                min_minor=60_000_00,
                mid_minor=70_000_00,
                max_minor=80_000_00,
            ),
        ]
    )
    session.commit()
    return Reference(engineering.id, sales.id, se_l3.id, se_l4.id, ae_l2.id)


def hire_request(reference: Reference, **overrides: Any) -> HireRequest:
    """A hire request for Ravi Kumar, Software Engineer L3 in India, with any field overridden."""
    ravi = HireRequest(
        employee_code="EMP-04821",
        name="Ravi Kumar",
        email="ravi.kumar@acme.example",
        country_code="IN",
        role_id=reference.se_l3_id,
        employment_type=EmploymentType.FULL_TIME,
        fte=Decimal("1"),
        hire_date=date(2022, 3, 14),
        base_annual_minor=lakh(18_00_000),
    )
    return replace(ravi, **overrides)
