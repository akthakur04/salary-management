"""Reference data: countries, roles, role defaults, pay bands and the active FX rates."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.bands import PayBand as DomainPayBand
from app.domain.errors import InvalidFxRateError
from app.domain.fx import FxRates
from app.domain.money import Money
from app.domain.role_defaults import RoleDefaultComponent as DomainRoleDefault
from app.models import Country, FxRate, PayBand, Role, RoleDefaultComponent


class ReferenceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

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
        row = self._session.execute(
            select(PayBand, Country.currency)
            .join(Country, Country.code == PayBand.country_code)
            .where(PayBand.role_id == role_id, PayBand.country_code == country_code)
        ).one_or_none()
        if row is None:
            return None
        band, currency = row
        return DomainPayBand(
            Money(band.min_minor, currency),
            Money(band.mid_minor, currency),
            Money(band.max_minor, currency),
        )

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
