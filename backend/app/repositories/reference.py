"""Reference data: countries, roles, role defaults, pay bands and the active FX rates."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.bands import PayBand as DomainPayBand
from app.domain.errors import InvalidFxRateError
from app.domain.fx import FxRates
from app.domain.money import Money
from app.domain.role_defaults import RoleDefaultComponent as DomainRoleDefault
from app.models import Country, Department, FxRate, PayBand, Role, RoleDefaultComponent


@dataclass(frozen=True, slots=True)
class RoleListing:
    role: Role
    department: str
    defaults: tuple[DomainRoleDefault, ...]


@dataclass(frozen=True, slots=True)
class BandListing:
    role_id: int
    country_code: str
    band: DomainPayBand


class ReferenceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def countries(self) -> list[Country]:
        return list(self._session.scalars(select(Country).order_by(Country.code)))

    def departments(self) -> list[Department]:
        return list(self._session.scalars(select(Department).order_by(Department.name)))

    def roles(self) -> list[RoleListing]:
        defaults: dict[int, list[DomainRoleDefault]] = {}
        for row in self._session.scalars(
            select(RoleDefaultComponent).order_by(RoleDefaultComponent.id)
        ):
            defaults.setdefault(row.role_id, []).append(
                DomainRoleDefault(row.type, row.percent, row.label)
            )
        rows = self._session.execute(
            select(Role, Department.name)
            .join(Department, Department.id == Role.department_id)
            .order_by(Role.family, Role.level)
        )
        return [
            RoleListing(role, department, tuple(defaults.get(role.id, ())))
            for role, department in rows
        ]

    def role_listing(self, role_id: int) -> RoleListing | None:
        row = self._session.execute(
            select(Role, Department.name)
            .join(Department, Department.id == Role.department_id)
            .where(Role.id == role_id)
        ).one_or_none()
        if row is None:
            return None
        role, department = row
        return RoleListing(role, department, self.role_defaults(role_id))

    def country(self, country_code: str) -> Country | None:
        return self._session.get(Country, country_code)

    def pay_bands(
        self, role_id: int | None = None, country_code: str | None = None
    ) -> list[BandListing]:
        statement = (
            select(PayBand, Country.currency)
            .join(Country, Country.code == PayBand.country_code)
            .order_by(PayBand.role_id, PayBand.country_code)
        )
        if role_id is not None:
            statement = statement.where(PayBand.role_id == role_id)
        if country_code is not None:
            statement = statement.where(PayBand.country_code == country_code)
        return [
            BandListing(band.role_id, band.country_code, _to_domain_band(band, currency))
            for band, currency in self._session.execute(statement)
        ]

    def country_currency(self, country_code: str) -> str | None:
        return self._session.scalar(select(Country.currency).where(Country.code == country_code))

    def role(self, role_id: int) -> Role | None:
        return self._session.get(Role, role_id)

    def role_defaults(self, role_id: int) -> tuple[DomainRoleDefault, ...]:
        rows = self._session.scalars(
            select(RoleDefaultComponent)
            .where(RoleDefaultComponent.role_id == role_id)
            .order_by(RoleDefaultComponent.id)
        )
        return tuple(DomainRoleDefault(row.type, row.percent, row.label) for row in rows)

    def pay_band(self, role_id: int, country_code: str) -> DomainPayBand | None:
        bands = self.pay_bands(role_id, country_code)
        return bands[0].band if bands else None

    def active_fx_rates(self) -> FxRates:
        rows = self._session.execute(
            select(FxRate.rate_set, FxRate.currency, FxRate.usd_per_unit).where(FxRate.is_active)
        ).all()
        rate_sets = sorted({row.rate_set for row in rows})
        if len(rate_sets) > 1:
            raise InvalidFxRateError(
                "Exactly one FX rate set may be active.", active_rate_sets=rate_sets
            )
        return FxRates({row.currency: row.usd_per_unit for row in rows})


def _to_domain_band(band: PayBand, currency: str) -> DomainPayBand:
    return DomainPayBand(
        Money(band.min_minor, currency),
        Money(band.mid_minor, currency),
        Money(band.max_minor, currency),
    )
