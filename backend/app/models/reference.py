"""Job architecture and reference data: countries, FX rates, departments, roles, bands."""

from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.components import ComponentType
from app.models.base import Base
from app.models.types import ExactDecimal, string_enum


class Country(Base):
    __tablename__ = "country"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3))


class FxRate(Base):
    """Reference rates. Exactly one rate set is active; every USD figure uses it."""

    __tablename__ = "fx_rate"
    __table_args__ = (
        UniqueConstraint("rate_set", "currency"),
        Index("ix_fx_rate_is_active_currency", "is_active", "currency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rate_set: Mapped[str] = mapped_column(String(40))
    currency: Mapped[str] = mapped_column(String(3))
    usd_per_unit: Mapped[Decimal] = mapped_column(ExactDecimal(18, 10))
    is_active: Mapped[bool] = mapped_column(default=False)


class Department(Base):
    __tablename__ = "department"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Role(Base):
    """Job family plus level, e.g. Software Engineer L3."""

    __tablename__ = "role"
    __table_args__ = (
        UniqueConstraint("family", "level"),
        CheckConstraint("level BETWEEN 1 AND 5", name="level_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("department.id"), index=True)
    family: Mapped[str] = mapped_column(String(80))
    level: Mapped[int]
    title: Mapped[str] = mapped_column(String(120))


class RoleDefaultComponent(Base):
    """Template copied onto new hires: a bonus or commission as a percentage of base."""

    __tablename__ = "role_default_component"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), index=True)
    type: Mapped[ComponentType] = mapped_column(string_enum(ComponentType, "component_type"))
    percent: Mapped[Decimal] = mapped_column(ExactDecimal(5, 2))
    label: Mapped[str] = mapped_column(String(120))


class PayBand(Base):
    """Minimum, midpoint and maximum annual base for a role in a country, in local currency."""

    __tablename__ = "pay_band"
    __table_args__ = (
        UniqueConstraint("role_id", "country_code"),
        CheckConstraint(
            "min_minor > 0 AND min_minor <= mid_minor AND mid_minor <= max_minor",
            name="ordered",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"))
    country_code: Mapped[str] = mapped_column(ForeignKey("country.code"))
    min_minor: Mapped[int] = mapped_column(BigInteger)
    mid_minor: Mapped[int] = mapped_column(BigInteger)
    max_minor: Mapped[int] = mapped_column(BigInteger)
