"""Loading the demo data set: complete, idempotent, and readable through the app's own queries."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import FixedClock
from app.domain.money import Money
from app.models import (
    CompensationComponent,
    CompensationVersion,
    Country,
    Employee,
    FxRate,
    PayBand,
    Role,
)
from app.repositories.compensation import CompensationRepository
from app.repositories.employees import EmployeeQuery
from app.seed.generator import SEED_TODAY, generate
from app.seed.loader import seed_database
from app.services.directory import DirectoryService

SAMPLE = 200


def _count(session: Session, model: type[object]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _counts(session: Session) -> dict[str, int]:
    return {
        model.__name__: _count(session, model)
        for model in (Country, FxRate, Role, PayBand, Employee, CompensationVersion)
    }


def test_seed_loads_reference_data_employees_and_their_history(session: Session) -> None:
    result = seed_database(session, employees=SAMPLE)

    expected_versions = sum(len(e.versions) for e in generate(employees=SAMPLE).employees)
    assert result.loaded
    assert _counts(session) == {
        "Country": 8,
        "FxRate": 8,
        "Role": 125,
        "PayBand": 1_000,
        "Employee": SAMPLE,
        "CompensationVersion": expected_versions,
    }
    assert _count(session, CompensationComponent) > 0


def test_seeding_again_leaves_the_data_unchanged(session: Session) -> None:
    seed_database(session, employees=SAMPLE)
    before = _counts(session)

    result = seed_database(session, employees=SAMPLE)

    assert not result.loaded
    assert _counts(session) == before


def test_reset_reloads_identical_data(session: Session) -> None:
    seed_database(session, employees=SAMPLE)
    before = _counts(session)
    ravi_before = CompensationRepository(session).history(1)

    result = seed_database(session, employees=SAMPLE, reset=True)

    assert result.loaded
    assert _counts(session) == before
    assert CompensationRepository(session).history(1) == ravi_before


def test_seeded_history_reads_back_as_generated(session: Session) -> None:
    generated = generate(employees=SAMPLE)
    seed_database(session, employees=SAMPLE)

    for employee in generated.employees[:50]:
        stored = CompensationRepository(session).history(employee.id)
        assert tuple(entry.version for entry in stored) == employee.versions


def test_seeded_data_works_with_the_directory(session: Session) -> None:
    seed_database(session, employees=SAMPLE)
    directory = DirectoryService(session, FixedClock(SEED_TODAY))

    (ravi,) = directory.list(EmployeeQuery(q="Ravi Kumar")).items

    assert ravi.band is not None
    assert ravi.band.compa_ratio == Decimal("0.89")
    assert ravi.total_pay_usd == Money(36_316_80, "USD")
    assert ravi.record.role_title == "Software Engineer"
    assert ravi.record.level == 3
