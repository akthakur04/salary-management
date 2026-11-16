"""Default pay structure for a role, copied (never linked) onto each new hire.

Role defaults are percentages of base, because a role spans every country and
currency: "Engineering L4 gets a 15% bonus" means the same thing in India and
Germany, while a fixed amount would not. Fixed amounts are set per employee.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.domain.components import Component, ComponentType
from app.domain.errors import InvalidComponentError

_DEFAULTABLE_TYPES = {ComponentType.BONUS, ComponentType.COMMISSION}


@dataclass(frozen=True, slots=True)
class RoleDefaultComponent:
    type: ComponentType
    percent: Decimal
    label: str

    def __post_init__(self) -> None:
        if self.type not in _DEFAULTABLE_TYPES:
            raise InvalidComponentError(
                "Role defaults can only be a bonus or a commission.", type=self.type
            )
        self.to_component()

    def to_component(self) -> Component:
        if self.type is ComponentType.BONUS:
            return Component.bonus_percent(self.percent, self.label)
        return Component.commission_percent(self.percent, self.label)


def components_for_new_hire(defaults: Iterable[RoleDefaultComponent]) -> tuple[Component, ...]:
    return tuple(default.to_component() for default in defaults)


def override_component(
    components: Iterable[Component],
    component_type: ComponentType,
    replacement: Component | None,
) -> tuple[Component, ...]:
    """Replace every component of a type with `replacement`, or remove them when it is None."""
    kept = tuple(component for component in components if component.type is not component_type)
    return kept if replacement is None else (*kept, replacement)
