"""One element of pay. Its *type* says what it is; its *basis* says how it's calculated."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from app.domain.errors import (
    InvalidAmountError,
    InvalidComponentError,
    InvalidPercentageError,
    MissingPayoutDateError,
)
from app.domain.money import Money


class ComponentType(StrEnum):
    ALLOWANCE = "allowance"
    BONUS = "bonus"
    COMMISSION = "commission"
    ONE_TIME = "one_time"


class ComponentBasis(StrEnum):
    FIXED_AMOUNT = "fixed_amount"
    PERCENT_OF_BASE = "percent_of_base"


class Frequency(StrEnum):
    MONTHLY = "monthly"
    ANNUAL = "annual"
    ONCE = "once"


_ALLOWED_BASES = {
    ComponentType.ALLOWANCE: {ComponentBasis.FIXED_AMOUNT},
    ComponentType.BONUS: {ComponentBasis.FIXED_AMOUNT, ComponentBasis.PERCENT_OF_BASE},
    ComponentType.COMMISSION: {ComponentBasis.FIXED_AMOUNT, ComponentBasis.PERCENT_OF_BASE},
    ComponentType.ONE_TIME: {ComponentBasis.FIXED_AMOUNT},
}

_ALLOWED_FREQUENCIES = {
    ComponentType.ALLOWANCE: {Frequency.MONTHLY, Frequency.ANNUAL},
    ComponentType.BONUS: {Frequency.ANNUAL},
    ComponentType.COMMISSION: {Frequency.ANNUAL},
    ComponentType.ONE_TIME: {Frequency.ONCE},
}

_VARIABLE_TYPES = {ComponentType.BONUS, ComponentType.COMMISSION}
_MONTHS_PER_YEAR = 12
_MAX_PERCENT = Decimal(100)


@dataclass(frozen=True, slots=True)
class Component:
    type: ComponentType
    basis: ComponentBasis
    frequency: Frequency
    label: str
    amount: Money | None = None
    percent: Decimal | None = None
    payout_date: date | None = None

    def __post_init__(self) -> None:
        self._check_type_allows_basis_and_frequency()
        if self.basis is ComponentBasis.FIXED_AMOUNT:
            self._check_fixed_amount()
        else:
            self._check_percentage()
        self._check_payout_date()

    @classmethod
    def allowance(cls, label: str, amount: Money, frequency: Frequency) -> "Component":
        return cls(ComponentType.ALLOWANCE, ComponentBasis.FIXED_AMOUNT, frequency, label, amount)

    @classmethod
    def bonus_percent(cls, percent: Decimal, label: str = "Annual bonus") -> "Component":
        return cls(
            ComponentType.BONUS,
            ComponentBasis.PERCENT_OF_BASE,
            Frequency.ANNUAL,
            label,
            percent=percent,
        )

    @classmethod
    def bonus_fixed(cls, amount: Money, label: str = "Annual bonus") -> "Component":
        return cls(
            ComponentType.BONUS, ComponentBasis.FIXED_AMOUNT, Frequency.ANNUAL, label, amount
        )

    @classmethod
    def commission_percent(cls, percent: Decimal, label: str = "Sales commission") -> "Component":
        return cls(
            ComponentType.COMMISSION,
            ComponentBasis.PERCENT_OF_BASE,
            Frequency.ANNUAL,
            label,
            percent=percent,
        )

    @classmethod
    def commission_fixed(cls, amount: Money, label: str = "Sales commission") -> "Component":
        return cls(
            ComponentType.COMMISSION, ComponentBasis.FIXED_AMOUNT, Frequency.ANNUAL, label, amount
        )

    @classmethod
    def one_time(cls, label: str, amount: Money, payout_date: date) -> "Component":
        return cls(
            ComponentType.ONE_TIME,
            ComponentBasis.FIXED_AMOUNT,
            Frequency.ONCE,
            label,
            amount,
            payout_date=payout_date,
        )

    @property
    def is_recurring(self) -> bool:
        return self.type is not ComponentType.ONE_TIME

    @property
    def is_variable(self) -> bool:
        return self.type in _VARIABLE_TYPES

    def annual_value(self, base: Money) -> Decimal:
        """Exact annual value in minor units, before rounding. One-time payments count zero."""
        if not self.is_recurring:
            return Decimal(0)
        if self.percent is not None:
            return Decimal(base.amount_minor) * self.percent / _MAX_PERCENT
        assert self.amount is not None
        multiplier = _MONTHS_PER_YEAR if self.frequency is Frequency.MONTHLY else 1
        return Decimal(self.amount.amount_minor * multiplier)

    def _check_type_allows_basis_and_frequency(self) -> None:
        if self.basis not in _ALLOWED_BASES[self.type]:
            raise InvalidComponentError(
                f"A {self.type} can't be calculated as {self.basis}.",
                type=self.type,
                basis=self.basis,
            )
        if self.frequency not in _ALLOWED_FREQUENCIES[self.type]:
            raise InvalidComponentError(
                f"A {self.type} can't be paid {self.frequency}.",
                type=self.type,
                frequency=self.frequency,
            )

    def _check_fixed_amount(self) -> None:
        if self.amount is None or self.percent is not None:
            raise InvalidComponentError(
                "A fixed-amount component needs an amount and no percentage.", label=self.label
            )
        if not self.amount.is_positive():
            raise InvalidAmountError(
                "Component amounts must be greater than zero.",
                label=self.label,
                amount_minor=self.amount.amount_minor,
            )

    def _check_percentage(self) -> None:
        if self.percent is None or self.amount is not None:
            raise InvalidComponentError(
                "A percentage-of-base component needs a percentage and no amount.",
                label=self.label,
            )
        if not Decimal(0) < self.percent <= _MAX_PERCENT:
            raise InvalidPercentageError(
                "Enter a percentage above 0% and at most 100%.",
                label=self.label,
                percent=str(self.percent),
            )

    def _check_payout_date(self) -> None:
        if self.frequency is Frequency.ONCE and self.payout_date is None:
            raise MissingPayoutDateError(
                "A one-time payment needs the date it is paid.", label=self.label
            )
        if self.frequency is not Frequency.ONCE and self.payout_date is not None:
            raise InvalidComponentError(
                "Only one-time payments have a payout date.", label=self.label
            )
