"""Column types that behave the same on SQLite and Postgres."""

from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import Dialect, Enum, Numeric, String
from sqlalchemy.types import TypeDecorator, TypeEngine


class ExactDecimal(TypeDecorator[Decimal]):
    """A decimal stored exactly: NUMERIC on Postgres, text on SQLite.

    SQLite has no decimal type and would round values such as FX rates through
    floating point. Stored as text, they read back exactly, and SQLite still
    treats them as numbers in arithmetic.
    """

    impl = Numeric
    cache_ok = True

    def __init__(self, precision: int, scale: int) -> None:
        super().__init__()
        self.precision = precision
        self.scale = scale

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String(self.precision + 2))
        return dialect.type_descriptor(Numeric(self.precision, self.scale, asdecimal=True))

    def process_bind_param(self, value: Decimal | None, dialect: Dialect) -> Any:
        if value is None or dialect.name != "sqlite":
            return value
        return str(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> Decimal | None:
        if value is None:
            return None
        return value if isinstance(value, Decimal) else Decimal(str(value))


def string_enum(enum_class: type[StrEnum], name: str) -> Enum:
    """Store an enum by its value as VARCHAR with a CHECK constraint (portable, no native type)."""
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=max(len(member.value) for member in enum_class),
        values_callable=lambda members: [member.value for member in members],
    )
