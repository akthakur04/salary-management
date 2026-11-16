"""SQLAlchemy ORM tables. Importing this package registers every table on `Base.metadata`."""

from app.models.base import Base
from app.models.compensation import CompensationComponent, CompensationVersion
from app.models.employee import Employee
from app.models.reference import (
    Country,
    Department,
    FxRate,
    PayBand,
    Role,
    RoleDefaultComponent,
)

__all__ = [
    "Base",
    "CompensationComponent",
    "CompensationVersion",
    "Country",
    "Department",
    "Employee",
    "FxRate",
    "PayBand",
    "Role",
    "RoleDefaultComponent",
]
