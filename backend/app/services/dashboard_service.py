from __future__ import annotations

import math
import time
from typing import Any


KPI_LIBRARY: list[dict[str, Any]] = [
    {
        "id": "quality-incident-rate",
        "name": "Quality Incident Rate",
        "persona": "operations",
        "category": "quality",
        "value": 2.4,
        "target": 3.0,
        "unit": "%",
        "period": "QTD",
        "status": "healthy",
        "trend": "up",
        "delta": 0.5,
        "description": "Reported quality incidents compared with target tolerance.",
    },
    {
        "id": "service-uptime",
        "name": "Service Uptime",
        "persona": "operations",
        "category": "operations",
        "value": 99.2,
        "target": 98.0,
        "unit": "%",
        "period": "MTD",
        "status": "healthy",
        "trend": "up",
        "delta": 1.1,
        "description": "Overall device service uptime across critical sites.",
    },
    {
        "id": "customer-satisfaction",
        "name": "Customer Satisfaction",
        "persona": "sales",
        "category": "customer",
        "value": 91.0,
        "target": 90.0,
        "unit": "%",
        "period": "MTD",
        "status": "healthy",
        "trend": "up",
        "delta": 2.4,
        "description": "Customer feedback and support sentiment index.",
    },
    {
        "id": "sales-revenue",
        "name": "Sales Revenue",
        "persona": "sales",
        "category": "commercial",
        "value": 1250000,
        "target": 1200000,
        "unit": "USD",
        "period": "MTD",
        "status": "warning",
        "trend": "up",
        "delta": 35000,
        "description": "Commercial revenue vs plan for the assigned region.",
    },
]


RESPONSIBILITY_LIBRARY: dict[str, list[dict[str, Any]]] = {
    "operations": [
        {"title": "Field service readiness", "owner": "Ops lead", "due": "This week", "status": "On track"},
        {"title": "Escalation follow-up", "owner": "Support desk", "due": "Today", "status": "Needs review"},
    ],
    "sales": [
        {"title": "Account coverage review", "owner": "Sales manager", "due": "This week", "status": "On track"},
        {"title": "Pipeline follow-up", "owner": "Regional team", "due": "Tomorrow", "status": "Pending"},
    ],
}


ACTION_LIBRARY: dict[str, list[dict[str, Any]]] = {
    "operations": [
        {"title": "Review service backlog", "priority": "High", "kpi": "service-uptime"},
        {"title": "Approve calibration plan", "priority": "Medium", "kpi": "quality-incident-rate"},
    ],
    "sales": [
        {"title": "Confirm top accounts", "priority": "High", "kpi": "sales-revenue"},
        {"title": "Launch customer outreach", "priority": "Medium", "kpi": "customer-satisfaction"},
    ],
}


WORKFLOW_LIBRARY: dict[str, list[dict[str, Any]]] = {
    "operations": [
        {"step": "Incident triage", "status": "Complete"},
        {"step": "Service dispatch", "status": "In progress"},
        {"step": "Escalation review", "status": "Queued"},
    ],
    "sales": [
        {"step": "Account review", "status": "Complete"},
        {"step": "Renewal outreach", "status": "In progress"},
        {"step": "Forecast review", "status": "Queued"},
    ],
}


def filter_kpis_for_persona(kpis: list[dict[str, Any]], persona: str) -> list[dict[str, Any]]:
    return [kpi for kpi in kpis if kpi.get("persona") in {persona, "all"}]


def build_dashboard_payload(persona: str, viewer: dict[str, str] | None = None) -> dict[str, Any]:
    persona_name = persona or "operations"
    now = time.time()
    kpis = [dict(kpi) for kpi in filter_kpis_for_persona(KPI_LIBRARY, persona_name)]
    for kpi in kpis:
        base_value = float(kpi["value"])
        spread = max(abs(base_value) * 0.012, 0.2)
        values = [
            base_value + math.sin((now - (11 - index) * 10) / 18) * spread
            for index in range(12)
        ]
        kpi["value"] = round(values[-1], 2)
        kpi["series"] = [
            {"time": f"-{(11 - index) * 10}s", "value": round(value, 2)}
            for index, value in enumerate(values)
        ]
    return {
        "persona": persona_name,
        "viewer": viewer or {"name": "Demo User", "email": "demo@local.dev"},
        "updated_at": int(now * 1000),
        "status_panel": {
            "title": "Operational status",
            "summary": "Current business health indicators for this persona.",
            "items": [
                {"label": "Active alerts", "value": 3 if persona_name == "operations" else 1},
                {"label": "On-time actions", "value": 85},
                {"label": "Coverage", "value": "92%"},
            ],
        },
        "metric_panel": {
            "title": "KPI metrics",
            "items": [
                {"label": item["name"], "value": item["value"], "unit": item["unit"], "status": item["status"]}
                for item in kpis
            ],
        },
        "responsibility_panel": {
            "title": "Responsibilities",
            "items": RESPONSIBILITY_LIBRARY.get(persona_name, []),
        },
        "action_panel": {
            "title": "Actions",
            "items": ACTION_LIBRARY.get(persona_name, []),
        },
        "workflow_panel": {
            "title": "Workflow",
            "items": WORKFLOW_LIBRARY.get(persona_name, []),
        },
        "kpis": kpis,
        "personas": ["operations", "sales"],
    }
