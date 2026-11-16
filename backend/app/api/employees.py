"""Employee endpoints. Routers stay thin: parse, call a service, shape the response."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db_session
from app.core.clock import Clock
from app.domain.bands import BandPosition
from app.domain.employment import EmploymentStatus, EmploymentType
from app.repositories.employees import CURRENT_EMPLOYEES, EmployeeQuery, EmployeeSort
from app.repositories.pagination import MAX_PAGE_SIZE
from app.schemas.common import PageOut
from app.schemas.employees import (
    EmployeeProfileOut,
    EmployeeSummaryOut,
    EmployeeUpdateIn,
    HireIn,
    HistoryEntryOut,
    PreviewOut,
    PreviewSideOut,
    RevisionIn,
    TerminateIn,
)
from app.services.compensation import CompensationService
from app.services.csv_export import employees_csv
from app.services.directory import DirectoryService
from app.services.employees import EmployeeService
from app.services.profile import ProfileService

router = APIRouter(prefix="/employees", tags=["employees"])

DbSession = Annotated[Session, Depends(get_db_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]
AsOf = Annotated[date | None, Query(description="Defaults to today.")]


def employee_query(
    q: Annotated[str | None, Query(max_length=100, description="Name or code prefix")] = None,
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    department: Annotated[int | None, Query()] = None,
    role: Annotated[int | None, Query()] = None,
    level: Annotated[int | None, Query(ge=1, le=5)] = None,
    employment_type: Annotated[list[EmploymentType] | None, Query()] = None,
    status_: Annotated[
        list[EmploymentStatus] | None,
        Query(alias="status", description="Defaults to active and on leave"),
    ] = None,
    band_position: Annotated[BandPosition | None, Query()] = None,
    sort: Annotated[EmployeeSort, Query()] = EmployeeSort.NAME,
    order: Annotated[Literal["asc", "desc"], Query()] = "asc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 25,
) -> EmployeeQuery:
    return EmployeeQuery(
        q=q,
        country_code=country,
        department_id=department,
        role_id=role,
        level=level,
        employment_types=tuple(employment_type or ()),
        statuses=tuple(status_ or CURRENT_EMPLOYEES),
        band_position=band_position,
        sort=sort,
        descending=order == "desc",
        page=page,
        page_size=page_size,
    )


Filters = Annotated[EmployeeQuery, Depends(employee_query)]


@router.get("")
def list_employees(
    session: DbSession, clock: ClockDep, query: Filters, as_of: AsOf = None
) -> PageOut[EmployeeSummaryOut]:
    page = DirectoryService(session, clock).search(query, as_of)
    return PageOut(
        items=[EmployeeSummaryOut.from_entry(entry) for entry in page.items],
        total=page.total,
        page=page.page,
        page_size=page.page_size,
    )


@router.get("/export.csv", response_class=Response)
def export_employees(
    session: DbSession, clock: ClockDep, query: Filters, as_of: AsOf = None
) -> Response:
    day = as_of or clock.today()
    entries = DirectoryService(session, clock).export(query, day)
    return Response(
        content=employees_csv(entries),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="employees-{day.isoformat()}.csv"'},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def hire_employee(
    body: HireIn, session: DbSession, clock: ClockDep, response: Response
) -> EmployeeProfileOut:
    employee_id = EmployeeService(session).hire(body.to_request())
    response.headers["Location"] = f"/api/v1/employees/{employee_id}"
    return EmployeeProfileOut.of(ProfileService(session).get(employee_id, clock.today()))


@router.get("/{employee_id}")
def get_employee(
    employee_id: int, session: DbSession, clock: ClockDep, as_of: AsOf = None
) -> EmployeeProfileOut:
    return EmployeeProfileOut.of(ProfileService(session).get(employee_id, as_of or clock.today()))


@router.patch("/{employee_id}")
def update_employee(
    employee_id: int, body: EmployeeUpdateIn, session: DbSession, clock: ClockDep
) -> EmployeeProfileOut:
    EmployeeService(session).update_details(employee_id, body.to_update())
    return EmployeeProfileOut.of(ProfileService(session).get(employee_id, clock.today()))


@router.post("/{employee_id}/terminate")
def terminate_employee(
    employee_id: int, body: TerminateIn, session: DbSession, clock: ClockDep
) -> EmployeeProfileOut:
    EmployeeService(session).terminate(employee_id, body.termination_date)
    return EmployeeProfileOut.of(ProfileService(session).get(employee_id, clock.today()))


@router.get("/{employee_id}/compensation")
def compensation_history(
    employee_id: int, session: DbSession, clock: ClockDep, as_of: AsOf = None
) -> list[HistoryEntryOut]:
    history = ProfileService(session).history(employee_id, as_of or clock.today())
    return [HistoryEntryOut.of(entry) for entry in history]


@router.post("/{employee_id}/compensation", status_code=status.HTTP_201_CREATED)
def revise_compensation(
    employee_id: int, body: RevisionIn, session: DbSession, clock: ClockDep
) -> HistoryEntryOut:
    version_id = CompensationService(session).revise(employee_id, body.to_request())
    return HistoryEntryOut.of(ProfileService(session).entry(employee_id, version_id, clock.today()))


@router.post("/{employee_id}/compensation/preview")
def preview_compensation(
    employee_id: int, body: RevisionIn, session: DbSession, clock: ClockDep
) -> PreviewOut:
    preview = CompensationService(session).preview(employee_id, body.to_request(), clock.today())
    return PreviewOut(
        before=PreviewSideOut.of(preview.before) if preview.before else None,
        after=PreviewSideOut.of(preview.after),
        base_change_percent=preview.base_change_percent,
        takes_effect_later=preview.takes_effect_later,
    )
