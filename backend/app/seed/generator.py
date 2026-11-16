"""Deterministic generator for ACME's demo data: 10,000 employees with salary histories.

Pure Python, no database. A fixed random seed and fixed dates make every run
identical. Each employee's history is built with the domain's `plan_revision`, so
the seed can only produce data the application itself would accept.

How an employee is made:
1. Pick country, department, job family, level and employment type by weight.
2. Pick their current base from a target position in the current band
   (~85% in band, the rest just below or above), then work backwards through
   past merits and promotions to the hire.
3. Optionally add a future-dated change on top (pending, E14).
4. Build each version's components: role defaults (with ~20% overrides),
   country allowances, and a sign-on bonus on some hires.
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from app.domain.bands import PayBand
from app.domain.components import Component, Frequency
from app.domain.employment import EmploymentStatus, EmploymentType
from app.domain.money import Money, round_half_even
from app.domain.package import CompensationPackage
from app.domain.role_defaults import RoleDefaultComponent
from app.domain.versions import (
    ChangeReason,
    CompensationChange,
    CompensationVersion,
    plan_revision,
)
from app.seed.names import NameBook
from app.seed.reference_data import (
    COUNTRIES,
    DEPARTMENT_WEIGHTS,
    FAMILIES,
    LEVEL_WEIGHTS,
    LEVELS,
    CountrySpec,
    FamilySpec,
    pay_band,
    role_defaults,
)

SEED_TODAY = date(2026, 11, 12)
DEFAULT_RANDOM_SEED = 20261112
EARLIEST_HIRE = date(2016, 1, 4)
LATEST_PAST_HIRE = date(2026, 10, 30)

MISSING_PACKAGE_EVERY = 833
FUTURE_HIRE_EVERY = 500
PART_TIME_FTES = (Decimal("0.5"), Decimal("0.6"), Decimal("0.75"), Decimal("0.8"))
VERSION_COUNT_WEIGHTS = {1: 10, 2: 20, 3: 35, 4: 35}

RAVI_CODE = "EMP-04821"


@dataclass(frozen=True, slots=True)
class SeedDepartment:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class SeedRole:
    id: int
    department_id: int
    family: str
    level: int
    title: str


@dataclass(frozen=True, slots=True)
class SeedBand:
    role_id: int
    country_code: str
    band: PayBand


@dataclass(frozen=True, slots=True)
class SeedEmployee:
    id: int
    employee_code: str
    name: str
    email: str
    employment_type: EmploymentType
    fte: Decimal
    status: EmploymentStatus
    hire_date: date
    termination_date: date | None
    versions: tuple[CompensationVersion, ...]


@dataclass(frozen=True, slots=True)
class SeedData:
    departments: tuple[SeedDepartment, ...]
    roles: tuple[SeedRole, ...]
    role_defaults: tuple[tuple[int, RoleDefaultComponent], ...]
    bands: tuple[SeedBand, ...]
    employees: tuple[SeedEmployee, ...]


def generate(employees: int = 10_000, random_seed: int = DEFAULT_RANDOM_SEED) -> SeedData:
    architecture = _Architecture()
    rng = random.Random(random_seed)
    names = NameBook(rng, reserved=("Ravi Kumar",))

    people = [_ravi_kumar(architecture, names)]
    codes = (f"EMP-{n:05d}" for n in range(1, employees + 2) if f"EMP-{n:05d}" != RAVI_CODE)
    for index, code in zip(range(1, employees), codes, strict=False):
        people.append(_Employee(rng, architecture, names, index + 1, code, index).build())

    return SeedData(
        departments=architecture.departments,
        roles=architecture.roles,
        role_defaults=architecture.role_default_rows,
        bands=architecture.bands,
        employees=tuple(people),
    )


class _Architecture:
    """Departments, roles (family and level), their defaults, and bands in every country."""

    def __init__(self) -> None:
        self.departments = tuple(
            SeedDepartment(id, name) for id, name in enumerate(DEPARTMENT_WEIGHTS, start=1)
        )
        department_ids = {department.name: department.id for department in self.departments}
        roles: list[SeedRole] = []
        self._role_by_key: dict[tuple[str, int], SeedRole] = {}
        self._family_by_name = {family.name: family for family in FAMILIES}
        for family in FAMILIES:
            for level in LEVELS:
                role = SeedRole(
                    id=len(roles) + 1,
                    department_id=department_ids[family.department],
                    family=family.name,
                    level=level,
                    title=family.name,
                )
                roles.append(role)
                self._role_by_key[(family.name, level)] = role
        self.roles = tuple(roles)
        self.role_default_rows = tuple(
            (role.id, default)
            for role in self.roles
            for default in role_defaults(self._family_by_name[role.family], role.level)
        )
        self.bands = tuple(
            SeedBand(role.id, country.code, pay_band(self.family(role), role.level, country))
            for role in self.roles
            for country in COUNTRIES
        )
        self._band_by_key = {(band.role_id, band.country_code): band.band for band in self.bands}

    def role(self, family: FamilySpec, level: int) -> SeedRole:
        return self._role_by_key[(family.name, level)]

    def family(self, role: SeedRole) -> FamilySpec:
        return self._family_by_name[role.family]

    def band(self, family: FamilySpec, level: int, country: CountrySpec) -> PayBand:
        return self._band_by_key[(self.role(family, level).id, country.code)]


@dataclass(frozen=True, slots=True)
class _Step:
    """One version to create: when, why, at which level, and the base salary."""

    effective_from: date
    reason: ChangeReason
    level: int
    base_units: int


@dataclass(slots=True)
class _Profile:
    family: FamilySpec
    country: CountrySpec
    employment_type: EmploymentType
    fte: Decimal
    override: str | None = None
    sign_on_units: int | None = None
    steps: list[_Step] = field(default_factory=list)


def _versions(profile: _Profile, architecture: _Architecture) -> tuple[CompensationVersion, ...]:
    history: tuple[CompensationVersion, ...] = ()
    for index, step in enumerate(profile.steps):
        role = architecture.role(profile.family, step.level)
        components = _components(profile, step, is_hire=index == 0)
        package = CompensationPackage(
            Money(step.base_units * 100, profile.country.currency), components
        )
        change = CompensationChange(
            step.effective_from, step.reason, role.id, profile.country.code, package
        )
        history = plan_revision(history, change, profile.country.currency).history_after(history)
    return history


def _components(profile: _Profile, step: _Step, is_hire: bool) -> tuple[Component, ...]:
    if profile.employment_type is EmploymentType.CONTRACTOR:
        return ()
    currency = profile.country.currency
    components = [*_allowances(profile.country, step.base_units)]
    defaults = role_defaults(profile.family, step.level)
    components.extend(_apply_override(defaults, profile.override))
    if is_hire and profile.sign_on_units is not None:
        components.append(
            Component.one_time(
                "Sign-on bonus", Money(profile.sign_on_units * 100, currency), step.effective_from
            )
        )
    return tuple(components)


def _allowances(country: CountrySpec, base_units: int) -> list[Component]:
    def monthly(label: str, units: int) -> Component:
        return Component.allowance(label, Money(units * 100, country.currency), Frequency.MONTHLY)

    match country.code:
        case "IN":
            housing = _round_to(Decimal(base_units) * Decimal("0.15") / 12, 100)
            return [monthly("Housing allowance", housing), monthly("Meal allowance", 2_200)]
        case "BR":
            return [monthly("Meal allowance", 1_000)]
        case "SG":
            return [monthly("Transport allowance", 200)]
        case _:
            return []


def _apply_override(
    defaults: tuple[RoleDefaultComponent, ...], override: str | None
) -> list[Component]:
    """Role defaults, adjusted by the employee's override (E3), as of this version's level."""
    if override == "remove":
        return []
    if override == "add" and not defaults:
        return [Component.bonus_percent(Decimal("5"))]
    adjustment = {"raise": 5, "add": 5, "lower": -5}.get(override or "", 0)
    return [
        RoleDefaultComponent(
            default.type, min(Decimal(100), default.percent + adjustment), default.label
        ).to_component()
        for default in defaults
    ]


def _round_to(value: Decimal, step: int) -> int:
    return round_half_even(value / step) * step


class _Employee:
    def __init__(
        self,
        rng: random.Random,
        architecture: _Architecture,
        names: NameBook,
        employee_id: int,
        code: str,
        index: int,
    ) -> None:
        self.rng = rng
        self.architecture = architecture
        self.names = names
        self.id = employee_id
        self.code = code
        self.index = index

    def build(self) -> SeedEmployee:
        rng = self.rng
        country = rng.choices(COUNTRIES, weights=[c.headcount_weight for c in COUNTRIES])[0]
        department = rng.choices(
            list(DEPARTMENT_WEIGHTS), weights=list(DEPARTMENT_WEIGHTS.values())
        )[0]
        family = rng.choice([f for f in FAMILIES if f.department == department])
        level = rng.choices(LEVELS, weights=LEVEL_WEIGHTS)[0]
        employment_type, fte = self._employment()
        name, email = self.names.person(country.code)
        profile = _Profile(family, country, employment_type, fte)

        is_missing = self.index % MISSING_PACKAGE_EVERY == 0
        is_future_hire = self.index % FUTURE_HIRE_EVERY == FUTURE_HIRE_EVERY // 2
        roll = rng.random()
        terminated = roll < 0.05 and not (is_missing or is_future_hire)
        status = EmploymentStatus.ON_LEAVE if 0.05 <= roll < 0.07 else EmploymentStatus.ACTIVE

        if is_future_hire:
            hire_date = SEED_TODAY + timedelta(days=rng.randint(20, 75))
        else:
            hire_date = EARLIEST_HIRE + timedelta(
                days=rng.randint(0, (LATEST_PAST_HIRE - EARLIEST_HIRE).days)
            )

        versions: tuple[CompensationVersion, ...] = ()
        if not is_missing:
            gets_sign_on = False
            if employment_type is not EmploymentType.CONTRACTOR:
                profile.override = self._override(family, level)
                gets_sign_on = rng.random() < 0.10
            profile.steps = self._steps(profile, level, hire_date, is_future_hire, terminated)
            if gets_sign_on:
                hire_base = Decimal(profile.steps[0].base_units)
                profile.sign_on_units = _round_to(
                    hire_base * Decimal(str(rng.uniform(0.05, 0.10))), 100
                )
            versions = _versions(profile, self.architecture)

        termination_date = self._termination_date(versions, hire_date) if terminated else None
        return SeedEmployee(
            id=self.id,
            employee_code=self.code,
            name=name,
            email=email,
            employment_type=employment_type,
            fte=fte,
            status=status,
            hire_date=hire_date,
            termination_date=termination_date,
            versions=versions,
        )

    def _employment(self) -> tuple[EmploymentType, Decimal]:
        roll = self.rng.random()
        if roll < 0.85:
            return EmploymentType.FULL_TIME, Decimal(1)
        if roll < 0.93:
            return EmploymentType.PART_TIME, self.rng.choice(PART_TIME_FTES)
        return EmploymentType.CONTRACTOR, Decimal(1)

    def _override(self, family: FamilySpec, level: int) -> str | None:
        if self.rng.random() >= 0.20:
            return None
        if not role_defaults(family, level):
            return "add"
        return self.rng.choice(("raise", "lower", "remove"))

    def _steps(
        self,
        profile: _Profile,
        current_level: int,
        hire_date: date,
        is_future_hire: bool,
        terminated: bool,
    ) -> list[_Step]:
        rng = self.rng
        if is_future_hire:
            base = self._current_base(profile, current_level)
            return [_Step(hire_date, ChangeReason.HIRE, current_level, base)]

        version_count = rng.choices(
            list(VERSION_COUNT_WEIGHTS), weights=list(VERSION_COUNT_WEIGHTS.values())
        )[0]
        has_pending = not terminated and rng.random() < 0.04
        if has_pending:
            version_count = max(version_count, 2)
        candidates = [
            date(year, 4, 1)
            for year in range(hire_date.year + 1, SEED_TODAY.year + 1)
            if hire_date < date(year, 4, 1) <= SEED_TODAY
        ]
        past_count = min(version_count - 1 - int(has_pending), len(candidates))
        past_dates = sorted(rng.sample(candidates, past_count))

        # Walk backwards from today's pay to the hire.
        level = current_level
        base = self._current_base(profile, level)
        backwards: list[_Step] = []
        for effective_from in reversed(past_dates):
            if level > 1 and rng.random() < 0.3:
                reason, raise_percent = ChangeReason.PROMOTION, rng.uniform(10, 15)
            elif rng.random() < 0.8:
                reason, raise_percent = ChangeReason.MERIT, rng.uniform(3, 10)
            else:
                reason, raise_percent = ChangeReason.MARKET_ADJUSTMENT, rng.uniform(5, 12)
            backwards.append(_Step(effective_from, reason, level, base))
            if reason is ChangeReason.PROMOTION:
                level -= 1
            base = _round_to(Decimal(base) / Decimal(str(1 + raise_percent / 100)), 100)
        steps = [_Step(hire_date, ChangeReason.HIRE, level, base), *reversed(backwards)]

        if has_pending:
            latest = steps[-1]
            promote = latest.level < 5 and rng.random() < 0.3
            raise_percent = rng.uniform(10, 15) if promote else rng.uniform(3, 8)
            steps.append(
                _Step(
                    SEED_TODAY + timedelta(days=rng.randint(10, 140)),
                    ChangeReason.PROMOTION if promote else ChangeReason.MERIT,
                    latest.level + int(promote),
                    _round_to(
                        Decimal(latest.base_units) * Decimal(str(1 + raise_percent / 100)), 100
                    ),
                )
            )
        return steps

    def _current_base(self, profile: _Profile, level: int) -> int:
        """Base salary in whole local units, placed against the current band (FTE-adjusted)."""
        band = self.architecture.band(profile.family, level, profile.country)
        minimum = Decimal(band.minimum.amount_minor) / 100
        maximum = Decimal(band.maximum.amount_minor) / 100
        roll = self.rng.random()
        if roll < 0.85:
            equivalent = minimum + (maximum - minimum) * Decimal(str(self.rng.uniform(0.03, 0.97)))
        elif roll < 0.925:
            equivalent = minimum * Decimal(str(self.rng.uniform(0.85, 0.98)))
        else:
            equivalent = maximum * Decimal(str(self.rng.uniform(1.02, 1.12)))
        return _round_to(equivalent * profile.fte, 100)

    def _termination_date(self, versions: tuple[CompensationVersion, ...], hire_date: date) -> date:
        """A past last day, after the latest version started, so nothing is due after it."""
        latest_start = versions[-1].effective_from if versions else hire_date
        earliest = min(latest_start + timedelta(days=30), SEED_TODAY - timedelta(days=1))
        span = (SEED_TODAY - timedelta(days=1) - earliest).days
        return earliest + timedelta(days=self.rng.randint(0, max(span, 0)))


def _ravi_kumar(architecture: _Architecture, names: NameBook) -> SeedEmployee:
    """The demo scenario's employee, exactly as on the profile design."""
    software_engineer = next(f for f in FAMILIES if f.name == "Software Engineer")
    india = next(c for c in COUNTRIES if c.code == "IN")
    profile = _Profile(
        software_engineer,
        india,
        EmploymentType.FULL_TIME,
        Decimal(1),
        sign_on_units=1_50_000,
        steps=[
            _Step(date(2022, 3, 14), ChangeReason.HIRE, 2, 18_00_000),
            _Step(date(2023, 4, 1), ChangeReason.MERIT, 2, 19_80_000),
            _Step(date(2024, 4, 1), ChangeReason.PROMOTION, 3, 22_00_000),
            _Step(date(2025, 4, 1), ChangeReason.MERIT, 3, 24_00_000),
        ],
    )
    return SeedEmployee(
        id=1,
        employee_code=RAVI_CODE,
        name="Ravi Kumar",
        email=names.reserve_email("Ravi", "Kumar"),
        employment_type=EmploymentType.FULL_TIME,
        fte=Decimal(1),
        status=EmploymentStatus.ACTIVE,
        hire_date=date(2022, 3, 14),
        termination_date=None,
        versions=_versions(profile, architecture),
    )
