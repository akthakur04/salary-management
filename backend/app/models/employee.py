"""Employees.

Role and country are not stored here: they belong to the compensation version
in force on a date, so a future-dated promotion or transfer takes effect on its
own date without a job to update this row.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.employment import EmploymentStatus, EmploymentType
from app.models.base import Base
from app.models.types import ExactDecimal, string_enum


class Employee(Base):
    __tablename__ = "employee"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    employment_type: Mapped[EmploymentType] = mapped_column(
        string_enum(EmploymentType, "employment_type"), index=True
    )
    fte: Mapped[Decimal] = mapped_column(ExactDecimal(3, 2))
    status: Mapped[EmploymentStatus] = mapped_column(
        string_enum(EmploymentStatus, "employment_status"), index=True
    )
    hire_date: Mapped[date]
    termination_date: Mapped[date | None]
