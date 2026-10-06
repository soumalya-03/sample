from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.demo_auth import get_demo_dashboard_context
from backend.app.db.models import User
from backend.app.services.demo_dashboard_service import (
    build_individual_dashboard_payload,
    list_demo_process_executions,
    list_demo_responsibilities,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/persona")
def get_dashboard_for_persona(
    include_process_executions: bool = False,
    context: tuple[User, dict[str, str]] = Depends(get_demo_dashboard_context),
) -> dict:
    user, assignment = context
    try:
        return build_individual_dashboard_payload(
            user.email,
            {"name": user.name, "email": user.email},
            assignment["persona_id"],
            include_process_executions=include_process_executions,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail="The demo KPI workbook is unavailable") from error


@router.get("/responsibilities")
def get_responsibilities(
    responsibility_id: str | None = None,
    status: Literal["Pending", "In Progress", "Completed", "Blocked", "Overdue"] | None = None,
    context: tuple[User, dict[str, str]] = Depends(get_demo_dashboard_context),
) -> dict:
    _, assignment = context
    try:
        return list_demo_responsibilities(
            assignment["persona_id"],
            responsibility_id=responsibility_id,
            status=status,
        ) or {
            "responsibilities": [],
            "status_filter": status,
        }
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail="The demo KPI workbook is unavailable") from error


@router.get("/responsibilities/{responsibility_id}")
def get_responsibility_details(
    responsibility_id: str,
    status: Literal["Pending", "In Progress", "Completed", "Blocked", "Overdue"] | None = None,
    context: tuple[User, dict[str, str]] = Depends(get_demo_dashboard_context),
) -> dict:
    _, assignment = context
    try:
        payload = list_demo_responsibilities(
            assignment["persona_id"],
            responsibility_id=responsibility_id,
            status=status,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail="The demo KPI workbook is unavailable") from error
    if payload is None:
        raise HTTPException(status_code=404, detail="Responsibility not found for this account")
    return payload


@router.get("/process-executions")
def get_process_executions(
    status: Literal["Pending", "Completed", "In Progress", "Failed"] | None = None,
    search: str | None = Query(default=None, max_length=120),
    process: str | None = Query(default=None, max_length=120),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    context: tuple[User, dict[str, str]] = Depends(get_demo_dashboard_context),
) -> dict:
    user, _ = context
    try:
        if date_from and date_to and date_from > date_to:
            raise HTTPException(status_code=422, detail="date_from must be on or before date_to")
        return list_demo_process_executions(
            user.email,
            status,
            search,
            process,
            date_from,
            date_to,
            limit,
            offset,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail="The demo KPI workbook is unavailable") from error
