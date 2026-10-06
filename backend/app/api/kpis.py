from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.demo_auth import get_demo_dashboard_context
from backend.app.db.models import User
from backend.app.services.demo_dashboard_service import list_demo_kpis

KpiPeriod = Literal["daily", "weekly", "monthly", "quarterly", "yearly"]

router = APIRouter(prefix="/api/kpis", tags=["kpis"])


def _load_kpis(
    user: User,
    assignment: dict[str, str],
    period: KpiPeriod,
    record_limit: int = 0,
    record_offset: int = 0,
) -> list[dict]:
    try:
        return list_demo_kpis(
            user.email,
            assignment["persona_id"],
            period,
            record_limit=record_limit,
            record_offset=record_offset,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail="The demo KPI workbook is unavailable") from error


@router.get("")
def get_kpis(
    period: KpiPeriod = "weekly",
    context: tuple[User, dict[str, str]] = Depends(get_demo_dashboard_context),
) -> dict:
    user, assignment = context
    kpis = _load_kpis(user, assignment, period)
    return {
        "period": period,
        "data_source": "DEMO / SYNTHETIC DATA",
        "kpis": kpis,
    }


@router.get("/{kpi_id}/details")
def get_kpi_details(
    kpi_id: str,
    period: KpiPeriod = "weekly",
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    context: tuple[User, dict[str, str]] = Depends(get_demo_dashboard_context),
) -> dict:
    user, assignment = context
    kpi = next(
        (
            item for item in _load_kpis(user, assignment, period, limit, offset)
            if item["kpi_id"] == kpi_id
        ),
        None,
    )
    if kpi is None:
        raise HTTPException(status_code=404, detail="KPI not found for this account")
    return kpi
