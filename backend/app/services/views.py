"""Read models shared by the profile, history and preview use cases.

Band position and USD are computed here at read time, against the band and FX
rates in force now, never stored.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.core.errors import NotFoundError
from app.domain.bands import BandComparison, PayBand, compare_to_band
from app.domain.fx import FxRates
from app.domain.money import Money
from app.domain.versions import CompensationVersion, base_change_percent
from app.models import Employee
from app.repositories.reference import ReferenceRepository


@dataclass(frozen=True, slots=True)
class RoleInfo:
    id: int
    title: str
    family: str
    level: int
    department: str


@dataclass(frozen=True, slots=True)
class BandView:
    band: PayBand | None
    comparison: BandComparison


@dataclass(frozen=True, slots=True)
class VersionView:
    """A version with its role, band comparison and USD total, as of now."""

    version: CompensationVersion
    role: RoleInfo
    band: BandView
    total_usd: Money


class Views:
    def __init__(self, reference: ReferenceRepository) -> None:
        self._reference = reference
        self._roles: dict[int, RoleInfo] = {}
        self._rates: FxRates | None = None

    def role(self, role_id: int) -> RoleInfo:
        if role_id not in self._roles:
            listing = self._reference.role_listing(role_id)
            if listing is None:
                raise NotFoundError("That role doesn't exist.", code="ROLE_NOT_FOUND")
            role = listing.role
            self._roles[role_id] = RoleInfo(
                role.id, role.title, role.family, role.level, listing.department
            )
        return self._roles[role_id]

    def rates(self) -> FxRates:
        if self._rates is None:
            self._rates = self._reference.active_fx_rates()
        return self._rates

    def band(self, employee: Employee, version: CompensationVersion) -> BandView:
        band = self._reference.pay_band(version.role_id, version.country_code)
        comparison = compare_to_band(
            version.package.base_annual, employee.fte, employee.employment_type, band
        )
        return BandView(band, comparison)

    def version(self, employee: Employee, version: CompensationVersion) -> VersionView:
        total = version.totals.total_target_compensation
        return VersionView(
            version=version,
            role=self.role(version.role_id),
            band=self.band(employee, version),
            total_usd=self.rates().to_usd(total),
        )


def change_percent(
    previous: CompensationVersion | None, new: CompensationVersion
) -> Decimal | None:
    """Base change from the previous version, in local currency (E19)."""
    return base_change_percent(previous.package, new.package) if previous else None
