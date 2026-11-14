"""Response models for the insights endpoints. All pay figures are USD at reference rates."""

from datetime import date

from pydantic import BaseModel

from app.domain.money import Money
from app.domain.stats import share_percent
from app.domain.versions import ChangeReason
from app.schemas.common import MoneyOut, OneDecimal
from app.schemas.employees import RoleRef
from app.services.insights import (
    BandGroup,
    ExceptionCounts,
    ExceptionItem,
    ExceptionType,
    PayGroup,
    RecentChange,
    Summary,
)


class SummaryOut(BaseModel):
    as_of: date
    headcount: int
    joiners_this_quarter: int
    leavers_this_quarter: int
    total_pay_usd: MoneyOut
    median_pay_usd: MoneyOut | None
    paid_within_band_percent: OneDecimal | None
    bonus_eligible_percent: OneDecimal | None
    variable_share_percent: OneDecimal | None
    employees_without_package: int

    @classmethod
    def of(cls, summary: Summary) -> "SummaryOut":
        return cls(
            as_of=summary.as_of,
            headcount=summary.headcount,
            joiners_this_quarter=summary.joiners_this_quarter,
            leavers_this_quarter=summary.leavers_this_quarter,
            total_pay_usd=MoneyOut.of(summary.total_pay_usd),
            median_pay_usd=MoneyOut.maybe(summary.median_pay_usd),
            paid_within_band_percent=summary.paid_within_band_percent,
            bonus_eligible_percent=summary.bonus_eligible_percent,
            variable_share_percent=summary.variable_share_percent,
            employees_without_package=summary.employees_without_package,
        )


def _usd(amount_minor: int) -> MoneyOut:
    return MoneyOut.of(Money(amount_minor, "USD"))


class PayGroupOut(BaseModel):
    key: str
    label: str
    headcount: int
    minimum: MoneyOut
    median: MoneyOut
    mean: MoneyOut
    maximum: MoneyOut
    variable_share_percent: OneDecimal | None

    @classmethod
    def of(cls, group: PayGroup) -> "PayGroupOut":
        summary = group.summary
        return cls(
            key=group.key,
            label=group.label,
            headcount=summary.count,
            minimum=_usd(summary.minimum),
            median=_usd(summary.median),
            mean=_usd(summary.mean),
            maximum=_usd(summary.maximum),
            variable_share_percent=group.variable_share_percent,
        )


class BandGroupOut(BaseModel):
    key: str
    label: str
    below: int
    in_band: int
    above: int
    banded: int
    in_band_percent: OneDecimal | None

    @classmethod
    def of(cls, group: BandGroup) -> "BandGroupOut":
        distribution = group.distribution
        return cls(
            key=group.key,
            label=group.label,
            below=distribution.below,
            in_band=distribution.in_band,
            above=distribution.above,
            banded=distribution.banded,
            in_band_percent=share_percent(distribution.in_band, distribution.banded),
        )


class ExceptionCountsOut(BaseModel):
    below: int
    above: int
    pending: int
    missing: int
    total: int

    @classmethod
    def of(cls, counts: ExceptionCounts) -> "ExceptionCountsOut":
        return cls(
            below=counts.below,
            above=counts.above,
            pending=counts.pending,
            missing=counts.missing,
            total=counts.total,
        )


class ExceptionItemOut(BaseModel):
    employee_id: int
    employee_code: str
    name: str
    role: RoleRef | None
    country_code: str | None
    base_salary: MoneyOut | None
    band_minimum: MoneyOut | None
    band_maximum: MoneyOut | None
    gap: MoneyOut | None
    gap_percent: OneDecimal | None
    new_base_salary: MoneyOut | None
    effective_from: date | None
    reason: ChangeReason | None

    @classmethod
    def of(cls, item: ExceptionItem) -> "ExceptionItemOut":
        record, band, comparison = item.entry.record, item.entry.record.band, item.entry.band
        package = record.current
        gap = gap_percent = None
        if band is not None and comparison is not None:
            equivalent = comparison.fte_equivalent_base
            if equivalent < band.minimum:
                gap = band.minimum - equivalent
                share = share_percent(gap.amount_minor, band.minimum.amount_minor)
                gap_percent = -share if share is not None else None
            elif equivalent > band.maximum:
                gap = equivalent - band.maximum
                gap_percent = share_percent(gap.amount_minor, band.maximum.amount_minor)
        role = (
            RoleRef(id=record.role_id, title=record.role_title, level=record.level)
            if record.role_id is not None
            and record.role_title is not None
            and record.level is not None
            else None
        )
        return cls(
            employee_id=record.id,
            employee_code=record.employee_code,
            name=record.name,
            role=role,
            country_code=record.country_code,
            base_salary=(
                MoneyOut.of(Money(package.base_annual_minor, package.currency)) if package else None
            ),
            band_minimum=MoneyOut.of(band.minimum) if band else None,
            band_maximum=MoneyOut.of(band.maximum) if band else None,
            gap=MoneyOut.maybe(gap),
            gap_percent=gap_percent,
            new_base_salary=MoneyOut.maybe(item.new_base),
            effective_from=item.effective_from,
            reason=item.reason,
        )


class ExceptionsOut(BaseModel):
    counts: ExceptionCountsOut
    type: ExceptionType
    items: list[ExceptionItemOut]
    total: int
    page: int
    page_size: int


class RecentChangeOut(BaseModel):
    employee_id: int
    name: str
    role: RoleRef
    country_code: str
    reason: ChangeReason
    effective_from: date
    is_pending: bool
    base_change_percent: OneDecimal | None

    @classmethod
    def of(cls, change: RecentChange) -> "RecentChangeOut":
        return cls(
            employee_id=change.employee_id,
            name=change.name,
            role=RoleRef(id=change.role.id, title=change.role.title, level=change.role.level),
            country_code=change.country_code,
            reason=change.reason,
            effective_from=change.effective_from,
            is_pending=change.is_pending,
            base_change_percent=change.base_change_percent,
        )
