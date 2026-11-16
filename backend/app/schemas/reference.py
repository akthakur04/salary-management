from pydantic import BaseModel

from app.domain.components import ComponentType
from app.schemas.common import MoneyOut, Percent


class CountryOut(BaseModel):
    code: str
    name: str
    currency: str


class DepartmentOut(BaseModel):
    id: int
    name: str


class RoleDefaultOut(BaseModel):
    type: ComponentType
    percent: Percent
    label: str


class RoleOut(BaseModel):
    id: int
    department_id: int
    department: str
    family: str
    level: int
    title: str
    defaults: list[RoleDefaultOut]


class PayBandOut(BaseModel):
    role_id: int
    country_code: str
    minimum: MoneyOut
    midpoint: MoneyOut
    maximum: MoneyOut
