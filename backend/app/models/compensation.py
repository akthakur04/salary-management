"""Compensation history: immutable versions and their components.

A version stores only figures that depend on the version alone: the
local-currency totals. USD amounts and band position are computed at read time
against the active FX rates and the current pay band. The only change ever made
to a stored version is setting `effective_to` when a later version supersedes it.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.components import ComponentBasis, ComponentType, Frequency
from app.domain.versions import ChangeReason
from app.models.base import Base
from app.models.types import ExactDecimal, string_enum

_OPEN_VERSION = text("effective_to IS NULL")


class CompensationVersion(Base):
    __tablename__ = "compensation_version"
    __table_args__ = (
        Index(
            "ix_compensation_version_employee_id_effective_from", "employee_id", "effective_from"
        ),
        Index(
            "uq_compensation_version_one_open_per_employee",
            "employee_id",
            unique=True,
            sqlite_where=_OPEN_VERSION,
            postgresql_where=_OPEN_VERSION,
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from", name="period_order"
        ),
        CheckConstraint("base_annual_minor > 0", name="base_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    effective_from: Mapped[date]
    effective_to: Mapped[date | None]
    reason: Mapped[ChangeReason] = mapped_column(string_enum(ChangeReason, "change_reason"))
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), index=True)
    country_code: Mapped[str] = mapped_column(ForeignKey("country.code"), index=True)
    currency: Mapped[str] = mapped_column(String(3))
    base_annual_minor: Mapped[int] = mapped_column(BigInteger)
    fixed_cash_minor: Mapped[int] = mapped_column(BigInteger)
    target_variable_minor: Mapped[int] = mapped_column(BigInteger)
    ttc_minor: Mapped[int] = mapped_column(BigInteger)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )

    components: Mapped[list["CompensationComponent"]] = relationship(
        cascade="all, delete-orphan", order_by="CompensationComponent.id"
    )


class CompensationComponent(Base):
    __tablename__ = "compensation_component"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("compensation_version.id"), index=True)
    type: Mapped[ComponentType] = mapped_column(string_enum(ComponentType, "component_type"))
    basis: Mapped[ComponentBasis] = mapped_column(string_enum(ComponentBasis, "component_basis"))
    frequency: Mapped[Frequency] = mapped_column(string_enum(Frequency, "frequency"))
    label: Mapped[str] = mapped_column(String(120))
    amount_minor: Mapped[int | None] = mapped_column(BigInteger)
    percent: Mapped[Decimal | None] = mapped_column(ExactDecimal(5, 2))
    payout_date: Mapped[date | None]
