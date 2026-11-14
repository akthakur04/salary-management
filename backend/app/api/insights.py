"""Insights endpoints: the Overview, Insights and Exceptions screens."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db_session, get_settings_from_app
from app.core.clock import Clock
from app.core.config import Settings
from app.repositories.employees import EmployeeQuery
from app.repositories.pagination import MAX_PAGE_SIZE
from app.schemas.insights import (
    BandGroupOut,
    ExceptionCountsOut,
    ExceptionItemOut,
    ExceptionsOut,
    PayGroupOut,
    RecentChangeOut,
    SummaryOut,
)
from app.services.insights import ExceptionType, GroupBy, InsightsService

router = APIRouter(prefix="/insights", tags=["insights"])

AsOf = Annotated[date | None, Query(description="Defaults to today.")]


def insights_service(
    session: Annotated[Session, Depends(get_db_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> InsightsService:
    return InsightsService(session, clock, settings.pending_window_days)


Service = Annotated[InsightsService, Depends(insights_service)]


def group_filters(
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    department: Annotated[int | None, Query()] = None,
    level: Annotated[int | None, Query(ge=1, le=5)] = None,
) -> EmployeeQuery:
    return EmployeeQuery(country_code=country, department_id=department, level=level)


Filters = Annotated[EmployeeQuery, Depends(group_filters)]


@router.get("/summary")
def summary(service: Service, as_of: AsOf = None) -> SummaryOut:
    return SummaryOut.of(service.summary(as_of))


@router.get("/breakdown")
def breakdown(
    service: Service, filters: Filters, group_by: GroupBy = GroupBy.COUNTRY, as_of: AsOf = None
) -> list[PayGroupOut]:
    return [PayGroupOut.of(group) for group in service.breakdown(group_by, filters, as_of)]


@router.get("/band-distribution")
def band_distribution(
    service: Service, filters: Filters, group_by: GroupBy = GroupBy.DEPARTMENT, as_of: AsOf = None
) -> list[BandGroupOut]:
    return [BandGroupOut.of(group) for group in service.band_distribution(group_by, filters, as_of)]


@router.get("/exceptions")
def exceptions(
    service: Service,
    type_: Annotated[ExceptionType, Query(alias="type")] = ExceptionType.BELOW,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 25,
    as_of: AsOf = None,
) -> ExceptionsOut:
    counts, items = service.exceptions(type_, page, page_size, as_of)
    return ExceptionsOut(
        counts=ExceptionCountsOut.of(counts),
        type=type_,
        items=[ExceptionItemOut.of(item) for item in items.items],
        total=items.total,
        page=items.page,
        page_size=items.page_size,
    )


@router.get("/recent-changes")
def recent_changes(
    service: Service, limit: Annotated[int, Query(ge=1, le=50)] = 5, as_of: AsOf = None
) -> list[RecentChangeOut]:
    return [RecentChangeOut.of(change) for change in service.recent_changes(limit, as_of)]
