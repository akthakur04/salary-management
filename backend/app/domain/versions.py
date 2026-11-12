"""Effective-dated compensation history.

A version is immutable. A change appends a new version and closes the previous
one on the new effective date, so periods never overlap and history is never
overwritten. A version is in force when `effective_from <= as_of < effective_to`
(or it has no end).

Rules for a new change, measured against the latest version (the one with the
latest start date, which may itself be future-dated):

- It must start after the latest version starts.
- A `correction` may also start on the same date. It supersedes the latest
  version, which stays in history with a zero-length period.
- Anything earlier, including a correction dated between two existing versions,
  is rejected with OVERLAPPING_VERSION.
"""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from enum import StrEnum
from itertools import pairwise

from app.domain.errors import (
    CurrencyCountryMismatchError,
    InvalidChangeReasonError,
    InvalidEffectivePeriodError,
    OverlappingVersionError,
)
from app.domain.package import CompensationPackage, PackageTotals

_ONE_DECIMAL = Decimal("0.1")


class ChangeReason(StrEnum):
    HIRE = "hire"
    PROMOTION = "promotion"
    MERIT = "merit"
    MARKET_ADJUSTMENT = "market_adjustment"
    CORRECTION = "correction"


@dataclass(frozen=True, slots=True)
class CompensationChange:
    """A requested change, before it is placed in the history."""

    effective_from: date
    reason: ChangeReason
    role_id: int
    country_code: str
    package: CompensationPackage


@dataclass(frozen=True, slots=True)
class CompensationVersion:
    effective_from: date
    reason: ChangeReason
    role_id: int
    country_code: str
    package: CompensationPackage
    effective_to: date | None = None

    def __post_init__(self) -> None:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise InvalidEffectivePeriodError(
                "A version can't end before it starts.",
                effective_from=self.effective_from.isoformat(),
                effective_to=self.effective_to.isoformat(),
            )

    @property
    def totals(self) -> PackageTotals:
        return self.package.totals()

    @property
    def is_open(self) -> bool:
        return self.effective_to is None

    def is_in_force_on(self, as_of: date) -> bool:
        return self.effective_from <= as_of and (
            self.effective_to is None or as_of < self.effective_to
        )


@dataclass(frozen=True, slots=True)
class RevisionPlan:
    """What a change does to the history: close the previous version, add the new one.

    The service writes both in one transaction.
    """

    closed_previous: CompensationVersion | None
    new_version: CompensationVersion

    def history_after(
        self, history: Iterable[CompensationVersion]
    ) -> tuple[CompensationVersion, ...]:
        ordered = _in_order(history)
        if self.closed_previous is None:
            return (*ordered, self.new_version)
        return (*ordered[:-1], self.closed_previous, self.new_version)


def _in_order(history: Iterable[CompensationVersion]) -> tuple[CompensationVersion, ...]:
    """By start date; on a shared start date, a superseded (closed) version comes first."""
    return tuple(sorted(history, key=lambda v: (v.effective_from, v.is_open)))


def ensure_valid_history(history: Iterable[CompensationVersion]) -> None:
    ordered = _in_order(history)
    for earlier, later in pairwise(ordered):
        if earlier.effective_to is None or earlier.effective_to > later.effective_from:
            raise OverlappingVersionError(
                "Two compensation versions cover the same dates.",
                effective_from=later.effective_from.isoformat(),
                overlaps_version_effective_from=earlier.effective_from.isoformat(),
            )
    if ordered and not ordered[-1].is_open:
        raise InvalidEffectivePeriodError(
            "The latest compensation version must be open-ended.",
            effective_from=ordered[-1].effective_from.isoformat(),
        )


def current_version(
    history: Iterable[CompensationVersion], as_of: date
) -> CompensationVersion | None:
    return next((v for v in history if v.is_in_force_on(as_of)), None)


def pending_changes(
    history: Iterable[CompensationVersion], as_of: date
) -> tuple[CompensationVersion, ...]:
    """Saved changes that take effect after `as_of`."""
    return tuple(v for v in _in_order(history) if v.effective_from > as_of)


def changes_due_within(
    history: Iterable[CompensationVersion], as_of: date, days: int
) -> tuple[CompensationVersion, ...]:
    """Pending changes that take effect in the next `days` days."""
    horizon = as_of + timedelta(days=days)
    return tuple(v for v in pending_changes(history, as_of) if v.effective_from <= horizon)


def plan_revision(
    history: Iterable[CompensationVersion],
    change: CompensationChange,
    country_currency: str,
) -> RevisionPlan:
    """Check a change against the history and say which versions to write."""
    _ensure_currency_matches_country(change, country_currency)
    ordered = _in_order(history)
    ensure_valid_history(ordered)
    new_version = CompensationVersion(
        change.effective_from, change.reason, change.role_id, change.country_code, change.package
    )

    if not ordered:
        if change.reason is not ChangeReason.HIRE:
            raise InvalidChangeReasonError(
                "An employee's first compensation version must be their hire.",
                reason=change.reason,
            )
        return RevisionPlan(None, new_version)

    if change.reason is ChangeReason.HIRE:
        raise InvalidChangeReasonError(
            "An employee is hired once; record later changes with another reason.",
            reason=change.reason,
        )
    latest = ordered[-1]
    _ensure_change_follows_latest(change, latest)
    return RevisionPlan(replace(latest, effective_to=change.effective_from), new_version)


def base_change_percent(previous: CompensationPackage, new: CompensationPackage) -> Decimal | None:
    """Change in base salary, in local currency so FX can't distort it.

    None across a currency change, where a percentage would mean nothing.
    """
    if previous.currency != new.currency:
        return None
    old, updated = previous.base_annual.amount_minor, new.base_annual.amount_minor
    return (Decimal(updated - old) * 100 / old).quantize(_ONE_DECIMAL, rounding=ROUND_HALF_EVEN)


def _ensure_currency_matches_country(change: CompensationChange, country_currency: str) -> None:
    if change.package.currency != country_currency:
        raise CurrencyCountryMismatchError(
            f"Pay in {change.country_code} must be in {country_currency}.",
            country_code=change.country_code,
            expected_currency=country_currency,
            currency=change.package.currency,
        )


def _ensure_change_follows_latest(change: CompensationChange, latest: CompensationVersion) -> None:
    details = {
        "effective_from": change.effective_from.isoformat(),
        "latest_version_effective_from": latest.effective_from.isoformat(),
    }
    if change.effective_from < latest.effective_from:
        raise OverlappingVersionError(
            "A change can only start after the latest compensation version starts. "
            "Earlier periods are kept as recorded.",
            **details,
        )
    if change.effective_from == latest.effective_from and change.reason is not (
        ChangeReason.CORRECTION
    ):
        raise OverlappingVersionError(
            "A version already starts on this date. Record the change as a correction "
            "to replace it.",
            **details,
        )
