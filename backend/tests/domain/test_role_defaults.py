from decimal import Decimal

import pytest

from app.domain.components import Component, ComponentType
from app.domain.errors import InvalidComponentError, InvalidPercentageError
from app.domain.money import Money
from app.domain.package import CompensationPackage
from app.domain.role_defaults import (
    RoleDefaultComponent,
    components_for_new_hire,
    override_component,
)

BASE = Money(100_000_00, "EUR")
L4_DEFAULTS = (RoleDefaultComponent(ComponentType.BONUS, Decimal("15"), "Annual bonus"),)


def test_new_hire_gets_the_role_defaults() -> None:
    components = components_for_new_hire(L4_DEFAULTS)

    assert components == (Component.bonus_percent(Decimal("15"), "Annual bonus"),)


def test_employee_can_override_a_role_default_without_changing_the_role() -> None:
    components = components_for_new_hire(L4_DEFAULTS)

    overridden = override_component(
        components, ComponentType.BONUS, Component.bonus_percent(Decimal("20"))
    )

    assert CompensationPackage(BASE, overridden).totals().target_variable == Money(20_000_00, "EUR")
    assert L4_DEFAULTS[0].percent == Decimal("15")


def test_employee_can_have_a_role_default_removed() -> None:
    components = components_for_new_hire(L4_DEFAULTS)

    removed = override_component(components, ComponentType.BONUS, None)

    assert CompensationPackage(BASE, removed).totals().target_variable == Money(0, "EUR")


def test_changing_a_role_default_does_not_change_existing_employees() -> None:
    existing = CompensationPackage(BASE, components_for_new_hire(L4_DEFAULTS))
    revised_defaults = (RoleDefaultComponent(ComponentType.BONUS, Decimal("18"), "Annual bonus"),)

    new_hire = CompensationPackage(BASE, components_for_new_hire(revised_defaults))

    assert existing.totals().target_variable == Money(15_000_00, "EUR")
    assert new_hire.totals().target_variable == Money(18_000_00, "EUR")


def test_sales_role_default_is_a_commission() -> None:
    defaults = (RoleDefaultComponent(ComponentType.COMMISSION, Decimal("40"), "Commission"),)

    (commission,) = components_for_new_hire(defaults)

    assert commission.type is ComponentType.COMMISSION
    assert commission.is_variable


def test_role_default_must_be_a_bonus_or_commission() -> None:
    with pytest.raises(InvalidComponentError):
        RoleDefaultComponent(ComponentType.ALLOWANCE, Decimal("10"), "Housing")


def test_role_default_percentage_outside_0_to_100_is_rejected() -> None:
    with pytest.raises(InvalidPercentageError):
        RoleDefaultComponent(ComponentType.BONUS, Decimal("150"), "Annual bonus")
