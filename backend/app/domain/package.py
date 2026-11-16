"""An employee's salary package: annual base plus components, all in one local currency.

All figures are annual. Totals are calculated exactly in minor units and rounded
half-to-even once, at the end. One-time payments are reported for the year they
are paid and never count towards total target compensation.
"""

from dataclasses import dataclass, replace
from decimal import ROUND_HALF_EVEN, Decimal

from app.domain.components import Component
from app.domain.errors import CurrencyMismatchError, InvalidAmountError
from app.domain.money import Money, round_half_even

_ONE_DECIMAL = Decimal("0.1")


@dataclass(frozen=True, slots=True)
class PackageTotals:
    """The local-currency totals stored on each compensation version."""

    fixed_cash: Money
    target_variable: Money
    total_target_compensation: Money


@dataclass(frozen=True, slots=True)
class CompensationPackage:
    base_annual: Money
    components: tuple[Component, ...] = ()

    def __post_init__(self) -> None:
        if not self.base_annual.is_positive():
            raise InvalidAmountError(
                "Base salary must be greater than zero.",
                amount_minor=self.base_annual.amount_minor,
            )
        for component in self.components:
            if component.amount is not None and component.amount.currency != self.currency:
                raise CurrencyMismatchError(
                    "Every component must be in the same currency as the base salary.",
                    label=component.label,
                    currencies=[self.currency, component.amount.currency],
                )

    @property
    def currency(self) -> str:
        return self.base_annual.currency

    def totals(self) -> PackageTotals:
        fixed = self._exact_fixed_cash()
        variable = self._exact_target_variable()
        return PackageTotals(
            fixed_cash=self._money(fixed),
            target_variable=self._money(variable),
            total_target_compensation=self._money(fixed + variable),
        )

    def variable_share_percent(self) -> Decimal:
        """Variable pay as a percentage of total target compensation, to one decimal place."""
        variable = self._exact_target_variable()
        total = self._exact_fixed_cash() + variable
        return (variable * 100 / total).quantize(_ONE_DECIMAL, rounding=ROUND_HALF_EVEN)

    def one_time_total_for_year(self, year: int) -> Money:
        paid = sum(
            (
                component.amount.amount_minor
                for component in self.components
                if not component.is_recurring
                and component.amount is not None
                and component.payout_date is not None
                and component.payout_date.year == year
            ),
            start=0,
        )
        return Money(paid, self.currency)

    def with_base(self, base_annual: Money) -> "CompensationPackage":
        return replace(self, base_annual=base_annual)

    def _exact_fixed_cash(self) -> Decimal:
        allowances = sum(
            (c.annual_value(self.base_annual) for c in self.components if not c.is_variable),
            start=Decimal(0),
        )
        return Decimal(self.base_annual.amount_minor) + allowances

    def _exact_target_variable(self) -> Decimal:
        return sum(
            (c.annual_value(self.base_annual) for c in self.components if c.is_variable),
            start=Decimal(0),
        )

    def _money(self, exact_minor: Decimal) -> Money:
        return Money(round_half_even(exact_minor), self.currency)
