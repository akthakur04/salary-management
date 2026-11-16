"""Request and response models for the employee endpoints."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.bands import BandComparison, BandPosition, PayBand
from app.domain.components import Component, ComponentBasis, ComponentType, Frequency
from app.domain.employment import EmploymentStatus, EmploymentType
from app.domain.money import Money
from app.domain.versions import ChangeReason, CompensationVersion
from app.schemas.common import Fte, MoneyOut, OneDecimal, Percent, Ratio
from app.services.directory import DirectoryEntry
from app.services.inputs import ComponentInput, DetailsUpdate, HireRequest, RevisionRequest
from app.services.profile import EmployeeProfile, HistoryEntry, VersionState
from app.services.views import BandView, RoleInfo, VersionView

# Responses -----------------------------------------------------------------------------


class RoleRef(BaseModel):
    id: int
    title: str
    level: int


class CountryRef(BaseModel):
    code: str
    name: str


class BandRangeOut(BaseModel):
    minimum: MoneyOut
    midpoint: MoneyOut
    maximum: MoneyOut

    @classmethod
    def maybe(cls, band: PayBand | None) -> "BandRangeOut | None":
        if band is None:
            return None
        return cls(
            minimum=MoneyOut.of(band.minimum),
            midpoint=MoneyOut.of(band.midpoint),
            maximum=MoneyOut.of(band.maximum),
        )


class BandComparisonOut(BaseModel):
    position: BandPosition
    compa_ratio: Ratio | None
    fte_equivalent_base: MoneyOut
    gap_to_minimum: MoneyOut | None

    @classmethod
    def of(cls, comparison: BandComparison) -> "BandComparisonOut":
        return cls(
            position=comparison.position,
            compa_ratio=comparison.compa_ratio,
            fte_equivalent_base=MoneyOut.of(comparison.fte_equivalent_base),
            gap_to_minimum=MoneyOut.maybe(comparison.gap_to_minimum),
        )


class BandOut(BandComparisonOut):
    band: BandRangeOut | None

    @classmethod
    def from_view(cls, view: BandView) -> "BandOut":
        return cls(
            **BandComparisonOut.of(view.comparison).model_dump(), band=BandRangeOut.maybe(view.band)
        )


class EmployeeSummaryOut(BaseModel):
    id: int
    employee_code: str
    name: str
    email: str
    role: RoleRef | None
    department: str | None
    country: CountryRef | None
    employment_type: EmploymentType
    fte: Fte
    status: EmploymentStatus
    base_salary: MoneyOut | None
    total_pay: MoneyOut | None
    total_pay_usd: MoneyOut | None
    band: BandComparisonOut | None
    last_change: date | None

    @classmethod
    def from_entry(cls, entry: DirectoryEntry) -> "EmployeeSummaryOut":
        record, package = entry.record, entry.record.current
        role = (
            RoleRef(id=record.role_id, title=record.role_title, level=record.level)
            if record.role_id is not None
            and record.role_title is not None
            and record.level is not None
            else None
        )
        country = (
            CountryRef(code=record.country_code, name=record.country_name)
            if record.country_code and record.country_name
            else None
        )
        return cls(
            id=record.id,
            employee_code=record.employee_code,
            name=record.name,
            email=record.email,
            role=role,
            department=record.department,
            country=country,
            employment_type=record.employment_type,
            fte=record.fte,
            status=record.status,
            base_salary=(
                MoneyOut.of(Money(package.base_annual_minor, package.currency)) if package else None
            ),
            total_pay=MoneyOut.of(Money(package.ttc_minor, package.currency)) if package else None,
            total_pay_usd=MoneyOut.maybe(entry.total_pay_usd),
            band=BandComparisonOut.of(entry.band) if entry.band else None,
            last_change=package.effective_from if package else None,
        )


class ComponentOut(BaseModel):
    type: ComponentType
    basis: ComponentBasis
    frequency: Frequency
    label: str
    amount: MoneyOut | None
    percent: Percent | None
    payout_date: date | None
    annual_amount: MoneyOut

    @classmethod
    def of(cls, component: Component, base: Money) -> "ComponentOut":
        annual = Money(round(component.annual_value(base)), base.currency)
        return cls(
            type=component.type,
            basis=component.basis,
            frequency=component.frequency,
            label=component.label,
            amount=MoneyOut.maybe(component.amount),
            percent=component.percent,
            payout_date=component.payout_date,
            annual_amount=MoneyOut.of(annual),
        )


def _components(version: CompensationVersion) -> list[ComponentOut]:
    base = version.package.base_annual
    return [ComponentOut.of(c, base) for c in version.package.components if c.is_recurring]


class PackageOut(BaseModel):
    version_id: int
    effective_from: date
    reason: ChangeReason
    base_salary: MoneyOut
    components: list[ComponentOut]
    fixed_cash: MoneyOut
    target_variable: MoneyOut
    total_target_compensation: MoneyOut
    total_target_compensation_usd: MoneyOut
    variable_share: OneDecimal

    @classmethod
    def of(cls, version_id: int, view: VersionView) -> "PackageOut":
        version, totals = view.version, view.version.totals
        return cls(
            version_id=version_id,
            effective_from=version.effective_from,
            reason=version.reason,
            base_salary=MoneyOut.of(version.package.base_annual),
            components=_components(version),
            fixed_cash=MoneyOut.of(totals.fixed_cash),
            target_variable=MoneyOut.of(totals.target_variable),
            total_target_compensation=MoneyOut.of(totals.total_target_compensation),
            total_target_compensation_usd=MoneyOut.of(view.total_usd),
            variable_share=version.package.variable_share_percent(),
        )


class HistoryEntryOut(BaseModel):
    version_id: int
    effective_from: date
    effective_to: date | None
    state: VersionState
    reason: ChangeReason
    role: RoleRef
    country_code: str
    base_salary: MoneyOut
    components: list[ComponentOut]
    fixed_cash: MoneyOut
    target_variable: MoneyOut
    total_target_compensation: MoneyOut
    base_change_percent: OneDecimal | None
    note: str | None

    @classmethod
    def of(cls, entry: HistoryEntry) -> "HistoryEntryOut":
        version, totals = entry.version, entry.version.totals
        return cls(
            version_id=entry.version_id,
            effective_from=version.effective_from,
            effective_to=version.effective_to,
            state=entry.state,
            reason=version.reason,
            role=_role_ref(entry.role),
            country_code=version.country_code,
            base_salary=MoneyOut.of(version.package.base_annual),
            components=_components(version),
            fixed_cash=MoneyOut.of(totals.fixed_cash),
            target_variable=MoneyOut.of(totals.target_variable),
            total_target_compensation=MoneyOut.of(totals.total_target_compensation),
            base_change_percent=entry.base_change_percent,
            note=entry.note,
        )


class OneTimePaymentOut(BaseModel):
    label: str
    amount: MoneyOut
    payout_date: date


class PeersOut(BaseModel):
    count: int
    median_base: MoneyOut | None


class RoleOut(RoleRef):
    family: str
    department: str


class EmployeeProfileOut(BaseModel):
    id: int
    employee_code: str
    name: str
    email: str
    employment_type: EmploymentType
    fte: Fte
    status: EmploymentStatus
    hire_date: date
    termination_date: date | None
    role: RoleOut | None
    country: CountryRef | None
    currency: str | None
    package: PackageOut | None
    band: BandOut | None
    peers: PeersOut
    pending_changes: list[HistoryEntryOut]
    one_time_payments: list[OneTimePaymentOut]

    @classmethod
    def of(cls, profile: EmployeeProfile) -> "EmployeeProfileOut":
        employee, role, country = profile.employee, profile.role, profile.country
        package = (
            PackageOut.of(profile.current_version_id, profile.current)
            if profile.current and profile.current_version_id is not None
            else None
        )
        return cls(
            id=employee.id,
            employee_code=employee.employee_code,
            name=employee.name,
            email=employee.email,
            employment_type=employee.employment_type,
            fte=employee.fte,
            status=profile.status,
            hire_date=employee.hire_date,
            termination_date=employee.termination_date,
            role=(
                RoleOut(
                    id=role.id,
                    title=role.title,
                    level=role.level,
                    family=role.family,
                    department=role.department,
                )
                if role
                else None
            ),
            country=CountryRef(code=country.code, name=country.name) if country else None,
            currency=country.currency if country else None,
            package=package,
            band=BandOut.from_view(profile.band) if profile.band else None,
            peers=PeersOut(
                count=profile.peers.count, median_base=MoneyOut.maybe(profile.peers.median_base)
            ),
            pending_changes=[HistoryEntryOut.of(entry) for entry in profile.pending],
            one_time_payments=[
                OneTimePaymentOut(
                    label=p.label, amount=MoneyOut.of(p.amount), payout_date=p.payout_date
                )
                for p in profile.one_time_payments
            ],
        )


def _role_ref(role: RoleInfo) -> RoleRef:
    return RoleRef(id=role.id, title=role.title, level=role.level)


class PreviewSideOut(BaseModel):
    role: RoleRef
    country_code: str
    base_salary: MoneyOut
    fixed_cash: MoneyOut
    target_variable: MoneyOut
    total_target_compensation: MoneyOut
    total_target_compensation_usd: MoneyOut
    band: BandOut

    @classmethod
    def of(cls, view: VersionView) -> "PreviewSideOut":
        version, totals = view.version, view.version.totals
        return cls(
            role=_role_ref(view.role),
            country_code=version.country_code,
            base_salary=MoneyOut.of(version.package.base_annual),
            fixed_cash=MoneyOut.of(totals.fixed_cash),
            target_variable=MoneyOut.of(totals.target_variable),
            total_target_compensation=MoneyOut.of(totals.total_target_compensation),
            total_target_compensation_usd=MoneyOut.of(view.total_usd),
            band=BandOut.from_view(view.band),
        )


class PreviewOut(BaseModel):
    before: PreviewSideOut | None
    after: PreviewSideOut
    base_change_percent: OneDecimal | None
    takes_effect_later: bool


# Requests ------------------------------------------------------------------------------


class ComponentIn(BaseModel):
    type: ComponentType
    basis: ComponentBasis
    frequency: Frequency
    label: str = Field(min_length=1, max_length=120)
    amount_minor: int | None = None
    percent: Decimal | None = None
    payout_date: date | None = None

    def to_input(self) -> ComponentInput:
        return ComponentInput(
            self.type,
            self.basis,
            self.frequency,
            self.label,
            self.amount_minor,
            self.percent,
            self.payout_date,
        )


def _inputs(components: list[ComponentIn] | None) -> tuple[ComponentInput, ...] | None:
    return None if components is None else tuple(c.to_input() for c in components)


class HireIn(BaseModel):
    employee_code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    country_code: str = Field(min_length=2, max_length=2)
    role_id: int
    employment_type: EmploymentType
    fte: Decimal = Field(gt=0, le=1)
    hire_date: date
    base_annual_minor: int
    components: list[ComponentIn] | None = Field(
        default=None, description="Leave out to use the role's defaults."
    )

    def to_request(self) -> HireRequest:
        return HireRequest(
            employee_code=self.employee_code,
            name=self.name,
            email=self.email,
            country_code=self.country_code,
            role_id=self.role_id,
            employment_type=self.employment_type,
            fte=self.fte,
            hire_date=self.hire_date,
            base_annual_minor=self.base_annual_minor,
            components=_inputs(self.components),
        )


class EmployeeUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=254)
    employment_type: EmploymentType | None = None
    fte: Decimal | None = Field(default=None, gt=0, le=1)
    status: Literal["active", "on_leave"] | None = None

    def to_update(self) -> DetailsUpdate:
        return DetailsUpdate(
            name=self.name,
            email=self.email,
            employment_type=self.employment_type,
            fte=self.fte,
            status=EmploymentStatus(self.status) if self.status else None,
        )


class TerminateIn(BaseModel):
    termination_date: date = Field(description="The last day worked; may be in the future.")


class RevisionIn(BaseModel):
    effective_from: date
    reason: ChangeReason
    base_annual_minor: int
    role_id: int | None = None
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    components: list[ComponentIn] | None = Field(
        default=None, description="Leave out to keep the latest version's recurring components."
    )
    note: str | None = Field(default=None, max_length=500)

    def to_request(self) -> RevisionRequest:
        return RevisionRequest(
            effective_from=self.effective_from,
            reason=self.reason,
            base_annual_minor=self.base_annual_minor,
            role_id=self.role_id,
            country_code=self.country_code,
            components=_inputs(self.components),
            note=self.note,
        )
