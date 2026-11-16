"""Reference data for the UI's pickers: countries, departments, roles and pay bands."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.repositories.reference import ReferenceRepository
from app.schemas.common import MoneyOut
from app.schemas.reference import CountryOut, DepartmentOut, PayBandOut, RoleDefaultOut, RoleOut

router = APIRouter(prefix="/reference", tags=["reference"])
DbSession = Annotated[Session, Depends(get_db_session)]


@router.get("/countries")
def countries(session: DbSession) -> list[CountryOut]:
    return [
        CountryOut(code=c.code, name=c.name, currency=c.currency)
        for c in ReferenceRepository(session).countries()
    ]


@router.get("/departments")
def departments(session: DbSession) -> list[DepartmentOut]:
    return [DepartmentOut(id=d.id, name=d.name) for d in ReferenceRepository(session).departments()]


@router.get("/roles")
def roles(session: DbSession) -> list[RoleOut]:
    return [
        RoleOut(
            id=listing.role.id,
            department_id=listing.role.department_id,
            department=listing.department,
            family=listing.role.family,
            level=listing.role.level,
            title=listing.role.title,
            defaults=[
                RoleDefaultOut(type=d.type, percent=d.percent, label=d.label)
                for d in listing.defaults
            ],
        )
        for listing in ReferenceRepository(session).roles()
    ]


@router.get("/pay-bands")
def pay_bands(
    session: DbSession,
    role_id: Annotated[int | None, Query()] = None,
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
) -> list[PayBandOut]:
    return [
        PayBandOut(
            role_id=listing.role_id,
            country_code=listing.country_code,
            minimum=MoneyOut.of(listing.band.minimum),
            midpoint=MoneyOut.of(listing.band.midpoint),
            maximum=MoneyOut.of(listing.band.maximum),
        )
        for listing in ReferenceRepository(session).pay_bands(role_id, country)
    ]
