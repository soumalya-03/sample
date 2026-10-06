from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.services.demo_accounts import DEMO_USERS

SOURCE = ROOT / "storage" / "Medical_Device_Business_Services_Inc_Mentor_08_09_2026.xlsx"
OUTPUT = ROOT / "data" / "demo_process_kpi_data.xlsx"
JSON_OUTPUT = ROOT / "data" / "demo_process_kpi_data.json"
PROCESSES = [
    ("PROC-ORDER-CAPTURE", "Capture Order", "ACT-CAPTURE", "Capture order request", 1, 90),
    ("PROC-ORDER-VALIDATE", "Validate Order", "ACT-VALIDATE", "Validate customer and order", 2, 120),
    ("PROC-ORDER-SUBMIT", "Submit Order", "ACT-SUBMIT", "Submit validated order", 3, 120),
    ("PROC-DELIVERY", "Delivery", "ACT-DELIVERY", "Confirm delivery status", 4, 180),
]
DEMO_ACCOUNT_COUNT_PER_KPI = 150
ROLE14_WEEKLY_RATES = {
    "account-review-completion": 0.85,
    "recommendation-acceptance-rate": 0.90,
    "commercial-support-accuracy": 0.92,
    "customer-follow-up-sla": 0.88,
    "opportunity-capture-rate": 0.75,
    "forecast-accuracy": 0.96,
    "retention-action-completion": 0.90,
}
ROLE14_ILLUSTRATIVE_TARGETS = {
    "account-review-completion": 90.0,
    "recommendation-acceptance-rate": 85.0,
    "commercial-support-accuracy": 90.0,
    "customer-follow-up-sla": 90.0,
    "opportunity-capture-rate": 70.0,
    "forecast-accuracy": 90.0,
    "retention-action-completion": 90.0,
}


def extract_responsibilities(source_path: Path) -> list[dict[str, Any]]:
    source = load_workbook(source_path, read_only=True, data_only=True)
    try:
        sheet = source["Role_Responsibilities"]
        role_number: int | None = None
        responsibilities = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            role_heading = row[1] if len(row) > 1 else None
            if isinstance(role_heading, str):
                match = re.match(r"^\s*(\d+)\.\s*(.+)$", role_heading)
                role_number = int(match.group(1)) if match else None
                continue
            if role_number is None or len(row) < 6 or not isinstance(row[2], str):
                continue
            responsibility = row[2].strip()
            if responsibility.casefold() == "responsibilities":
                continue
            metric_name = row[3].strip() if isinstance(row[3], str) else ""
            formula = _normalize_source_formula(row[4].strip()) if isinstance(row[4], str) else ""
            target_area = row[5].strip() if isinstance(row[5], str) else ""
            responsibilities.append({
                "responsibility_id": f"role-{role_number:02d}-{slug(metric_name)}",
                "persona_id": f"role-{role_number:02d}",
                "responsibility": responsibility,
                "metric_name": metric_name,
                "formula": formula,
                "target_area": target_area,
                "role_number": role_number,
            })
        return responsibilities
    finally:
        source.close()


def build_demo_resources(definitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    role_sheets = {
        definition["role_id"]: str(definition["source"]).split(" | ", 1)[-1]
        for definition in definitions
    }
    resources = [
        {
            "resource_id": "RES-OPS-001",
            "email": "admin@local.dev",
            "name": "Local Admin",
            "persona_id": "role-09",
            "persona_name": "Operations Manager",
            "source_role_sheet": role_sheets.get("role-09"),
        },
        {
            "resource_id": "RES-SALES-001",
            "email": "sales@local.dev",
            "name": "Jordan Lee",
            "persona_id": "role-14",
            "persona_name": "Sales Rep",
            "source_role_sheet": role_sheets.get("role-14"),
        },
    ]
    for user in DEMO_USERS:
        role_number = int(user["persona_id"].removeprefix("role-"))
        resources.append({
            "resource_id": f"RES-ROLE-{role_number:02d}",
            "email": user["email"],
            "name": user["name"],
            "persona_id": user["persona_id"],
            "persona_name": user["persona_name"],
            "source_role_sheet": role_sheets.get(user["persona_id"]),
        })
    return resources


def clean(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def add_sheet(workbook: Workbook, title: str, headers: list[str], rows: list[list[Any]]) -> None:
    sheet = workbook.create_sheet(title)
    sheet.append(headers)
    for row in rows:
        sheet.append([clean(value) for value in row])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="285C4D")
    for column in sheet.columns:
        width = min(max(max(len(str(cell.value or "")) for cell in column) + 2, 12), 38)
        sheet.column_dimensions[column[0].column_letter].width = width


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _component_labels(formula: str, aggregation: str) -> tuple[str | None, str | None]:
    if aggregation == "forecast_accuracy_percent":
        return "ABS(Forecast Volume − Actual Volume)", "Actual Volume"
    for separator in (" ÷ ", " / "):
        if separator in formula:
            numerator, denominator = formula.split(separator, 1)
            return numerator.strip(), denominator.strip()
    return None, None


def _normalize_source_formula(formula: str) -> str:
    return formula.replace("\ufffd", "÷")


def extract_kpi_definitions(source_path: Path) -> list[dict[str, Any]]:
    source = load_workbook(source_path, read_only=True, data_only=True)
    definitions: list[dict[str, Any]] = []
    for sheet_name in source.sheetnames:
        match = re.match(r"Role (\d+) - (.+)", sheet_name)
        if not match:
            continue
        role_id = f"role-{int(match.group(1)):02d}"
        role_name = match.group(2)
        for row in source[sheet_name].iter_rows(min_row=10, values_only=True):
            name = row[0] if len(row) > 0 else None
            formula = row[1] if len(row) > 1 else None
            if isinstance(name, str) and name.startswith("SIX-PHASE"):
                break
            if not isinstance(name, str) or not isinstance(formula, str) or not formula.strip():
                continue
            formula = _normalize_source_formula(formula)
            metric_id = f"{role_id}-{slug(name)}"
            lower_name = name.lower()
            if formula.startswith("1 − ABS("):
                unit, aggregation = "%", "forecast_accuracy_percent"
            elif "handle time" in lower_name or "resolution time" in lower_name:
                unit, aggregation = "minutes", "average"
            elif "satisfaction" in lower_name or "csat" in lower_name or "quality score" in lower_name:
                unit, aggregation = "score", "average"
            elif "calls handled" in lower_name:
                unit, aggregation = "calls", "count"
            else:
                unit, aggregation = "%", "ratio_percent"
            numerator_label, denominator_label = _component_labels(formula, aggregation)
            definitions.append(
                {
                    "kpi_id": metric_id,
                    "name": name,
                    "description": formula,
                    "definition": formula,
                    "formula": formula,
                    "role_id": role_id,
                    "role_name": role_name,
                    "driver": row[2] if len(row) > 2 else None,
                    "enterprise_linkage": row[3] if len(row) > 3 else None,
                    "leading_indicator": row[4] if len(row) > 4 else None,
                    "lagging_result": row[5] if len(row) > 5 else None,
                    "direction": row[6] if len(row) > 6 else None,
                    "numerator_label": numerator_label,
                    "denominator_label": denominator_label,
                    "unit": unit,
                    "aggregation": aggregation,
                    "source": f"{SOURCE.name} | {sheet_name}",
                    "illustrative": True,
                }
            )
            if role_id == "role-14":
                kpi_slug = metric_id.removeprefix("role-14-")
                definitions[-1]["target_value"] = ROLE14_ILLUSTRATIVE_TARGETS.get(kpi_slug)
                definitions[-1]["target_source"] = "Synthetic demo target; not supplied or approved by the source workbook"
                if not definitions[-1]["direction"]:
                    definitions[-1]["direction"] = "Increase"
    source.close()
    return definitions


def generate_demo_kpi_observations(
    definitions: list[dict[str, Any]],
    base_time: datetime,
) -> list[list[Any]]:
    observations: list[list[Any]] = []
    source_definitions = [definition for definition in definitions if definition["role_id"] != "role-17"]
    if not source_definitions:
        raise ValueError("No source-defined role KPIs were found in the business workbook")

    for definition in source_definitions:
        role_prefix = definition["role_id"]
        kpi_slug = definition["kpi_id"].removeprefix(f"{role_prefix}-")
        seed = sum(ord(character) for character in definition["kpi_id"])
        current_week_start = base_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=base_time.weekday())
        days_in_current_week = base_time.weekday() + 1
        base_rate = ROLE14_WEEKLY_RATES.get(kpi_slug, 0.72 + (seed % 1800) / 10000)
        for account_index in range(DEMO_ACCOUNT_COUNT_PER_KPI):
            week_index = account_index // 20
            week_member = account_index % 20
            cohort_size = min(20, DEMO_ACCOUNT_COUNT_PER_KPI - week_index * 20)
            week_adjustment = 0 if week_index == 0 else (week_index % 3 - 1) * 0.03
            week_rate = max(0.5, min(1.0, base_rate + week_adjustment))
            successful_accounts = round(week_rate * cohort_size)
            aggregation = definition["aggregation"]
            denominator: float | None = 1
            forecast_volume = None
            actual_volume = None
            if aggregation == "forecast_accuracy_percent":
                denominator = float(1000 + account_index * 37)
                numerator = round(denominator * (1 - week_rate))
                forecast_volume = denominator - numerator
                actual_volume = denominator
            elif aggregation == "average":
                if definition["unit"] == "score":
                    individual_value = round(3.5 + week_rate * 1.5 + ((account_index % 5) - 2) * 0.05, 2)
                    denominator = 10
                else:
                    individual_value = round(35 + (1 - week_rate) * 70 + account_index % 8, 2)
                    denominator = float(8 + account_index % 8)
                numerator = round(individual_value * denominator, 2)
            elif aggregation == "count":
                numerator = 25 + int(week_rate * 30) + account_index % 12
                denominator = None
            elif role_prefix == "role-09" and kpi_slug == "overall-sla-achievement":
                numerator = 93
                denominator = 100
            else:
                numerator = 1 if week_member < successful_accounts else 0

            observed_at = (
                current_week_start
                - timedelta(weeks=week_index)
                + timedelta(days=week_member % days_in_current_week, hours=week_member % 12)
            )
            observations.append([
                f"OBS-{definition['kpi_id']}-{account_index + 1:03d}",
                definition["kpi_id"],
                role_prefix,
                f"DEMO-{role_prefix.upper()}-ACCOUNT-{account_index + 1:03d}",
                f"Synthetic {definition['role_name']} Account {account_index + 1:03d}",
                observed_at,
                numerator,
                denominator,
                "Forecast Volume" if aggregation == "forecast_accuracy_percent" else definition["numerator_label"],
                forecast_volume if aggregation == "forecast_accuracy_percent" else numerator,
                "Actual Volume" if aggregation == "forecast_accuracy_percent" else definition["denominator_label"],
                actual_volume if aggregation == "forecast_accuracy_percent" else denominator,
                "Forecast Accuracy" if aggregation == "forecast_accuracy_percent" else definition["name"],
                _observation_value(definition, numerator, denominator),
                "DEMO/SYNTHETIC",
                True,
            ])
    return observations


def generate_weekly_measurements(
    observations: list[list[Any]],
    definitions: list[dict[str, Any]],
    resources: list[dict[str, Any]],
) -> list[list[Any]]:
    definitions_by_id = {definition["kpi_id"]: definition for definition in definitions}
    observations_by_kpi_week: dict[tuple[str, date], list[list[Any]]] = {}
    for observation in observations:
        observed_at = observation[5]
        week_start = (observed_at - timedelta(days=observed_at.weekday())).date()
        observations_by_kpi_week.setdefault((observation[1], week_start), []).append(observation)
    emails_by_role: dict[str, list[str]] = {}
    for resource in resources:
        emails_by_role.setdefault(resource["persona_id"], []).append(resource["email"])

    measurements: list[list[Any]] = []
    for kpi_id in sorted({observation[1] for observation in observations}):
        weeks = sorted(
            (week_start for observed_kpi, week_start in observations_by_kpi_week if observed_kpi == kpi_id),
            reverse=True,
        )[:4]
        definition = definitions_by_id[kpi_id]
        for period_index, week_start in enumerate(reversed(weeks), 1):
            rows = observations_by_kpi_week[(kpi_id, week_start)]
            numerator = sum(row[6] for row in rows)
            denominator = sum(row[7] or 0 for row in rows)
            for email in emails_by_role.get(definition["role_id"], []):
                measurements.append([
                    f"MEAS-{kpi_id}-{email}-{period_index}",
                    kpi_id,
                    email,
                    week_start,
                    week_start + timedelta(days=6),
                    numerator,
                    denominator if definition["aggregation"] != "count" else None,
                    definition["unit"],
                    len(rows),
                    "DEMO/SYNTHETIC account observations",
                    True,
                ])
    return measurements


def _observation_value(definition: dict[str, Any], numerator: float, denominator: float | None) -> float:
    aggregation = definition["aggregation"]
    if aggregation == "count":
        return round(numerator, 2)
    if not denominator:
        return 0.0
    if aggregation == "forecast_accuracy_percent":
        return round((1 - numerator / denominator) * 100, 2)
    if aggregation == "average":
        return round(numerator / denominator, 2)
    return round(numerator / denominator * 100, 2)


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Source business workbook not found: {SOURCE}")

    definitions = extract_kpi_definitions(SOURCE)
    responsibilities = extract_responsibilities(SOURCE)
    demo_resources = build_demo_resources(definitions)
    base_time = datetime.now(timezone.utc).replace(microsecond=0)
    request_rows: list[list[Any]] = []
    execution_rows: list[list[Any]] = []
    measurement_rows: list[list[Any]] = []
    alert_rows: list[list[Any]] = []
    outcome_rows: list[list[Any]] = []
    responsibility_work_rows: list[list[Any]] = []

    for resource in demo_resources:
        for request_number in range(1, 7):
            request_code = resource["resource_id"].removeprefix("RES-").replace("-", "")
            request_id = f"REQ-{request_code}-{request_number:03d}"
            created_at = base_time - timedelta(days=3 * request_number + (0 if resource["persona_id"] == "role-09" else 1))
            request_status = "Completed" if request_number in {1, 3, 5, 6} else "In Progress"
            if request_number == 4:
                request_status = "Overdue"
            request_rows.append(
                [request_id, f"SYN-CUSTOMER-{request_code}-{request_number:03d}", created_at, request_status,
                 resource["resource_id"], resource["persona_id"], "DEMO/SYNTHETIC", "Order-to-Delivery"]
            )

            for process_index, process in enumerate(PROCESSES):
                process_id, process_name, activity_id, task_name, sequence, sla_minutes = process
                execution_id = f"EXE-{request_id}-{sequence}"
                start_at = created_at + timedelta(minutes=sequence * 18 + request_number * 3)
                status = "Completed"
                duration = 32 + ((request_number * 13 + sequence * 17) % 100)
                failure_reason = None
                retry_count = 0
                ended_at: datetime | None = start_at + timedelta(minutes=duration)
                if request_number == 2 and sequence == 4:
                    status, ended_at, duration = "In Progress", None, None
                elif request_number == 4 and sequence == 3:
                    status, ended_at, duration = "In Progress", None, None
                    start_at = base_time - timedelta(hours=8)
                elif request_number == 4 and sequence == 4:
                    status, ended_at, duration = "Pending", None, None
                elif request_number == 3 and sequence == 2:
                    status, failure_reason = "Failed", "Synthetic validation failure for retry demonstration"
                    ended_at = start_at + timedelta(minutes=duration)
                    retry_count = 0
                elif request_number == 3 and sequence == 3:
                    retry_count = 1

                predecessor = PROCESSES[sequence - 2][0] if sequence > 1 else None
                successor = PROCESSES[sequence][0] if sequence < len(PROCESSES) else None
                execution_rows.append(
                    [
                        f"TX-{request_id}", request_id, None, execution_id, process_id,
                        predecessor, successor, f"ACT-{sequence:02d}", f"TASK-{sequence:02d}",
                        f"WF-{request_id}", sequence, f"CORR-{request_id}", process_name,
                        f"{process_name} activity", task_name, status, status, request_status,
                        "Failed" if status == "Failed" else status,
                        failure_reason, retry_count, "FUNCTION-OPERATIONS", resource["persona_id"],
                        resource["resource_id"], resource["email"], start_at - timedelta(minutes=12),
                        start_at - timedelta(minutes=7), start_at, created_at, start_at, start_at,
                        ended_at, duration, 7, 12, sla_minutes, sla_minutes, None, None,
                        "DEMO/SYNTHETIC", failure_reason, created_at.date().isoformat(),
                    ]
                )
                observed_minutes = duration if duration is not None else (base_time - start_at).total_seconds() / 60
                if status != "Pending" and observed_minutes > sla_minutes:
                    alert_id = f"ALT-{execution_id}"
                    alert_rows.append(
                        [alert_id, execution_id, request_id, process_id, resource["persona_id"],
                         resource["resource_id"], "SLA breach", "High", observed_minutes, sla_minutes,
                         "Open", base_time, "Synthetic elapsed time exceeded configured SLA"]
                    )
                    execution_rows[-1][-2] = alert_id
                    execution_rows[-1][-1] = "High"
                if request_number == 3 and sequence == 2:
                    retry = list(execution_rows[-1])
                    retry[3] = f"{retry[3]}-R1"
                    retry[15] = retry[16] = retry[17] = "Completed"
                    retry[18] = "Completed"
                    retry[19] = None
                    retry[20] = 1
                    retry_start = retry[31] + timedelta(minutes=5)
                    retry_end = retry_start + timedelta(minutes=max(25, int(duration) - 20))
                    retry[27] = retry_start
                    retry[30] = retry_start
                    retry[31] = retry_end
                    retry[32] = (retry_end - retry_start).total_seconds() / 60
                    retry[33] = 5
                    retry[34] = 5
                    retry[-2:] = [None, None]
                    execution_rows.append(retry)

            outcome_rows.append(
                [f"OUT-{request_id}", request_id, "Order delivery" if request_status == "Completed" else "Order fulfillment in progress",
                 "Synthetic outcome; no real customer data", "DEMO/SYNTHETIC"]
            )

    role_observations = generate_demo_kpi_observations(definitions, base_time)
    measurement_rows.extend(generate_weekly_measurements(role_observations, definitions, demo_resources))

    work_statuses = ["In Progress", "Pending", "Completed", "Blocked", "Overdue"]
    for responsibility_index, responsibility in enumerate(responsibilities):
        role_requests = [
            row[0] for row in request_rows
            if row[5] == responsibility["persona_id"]
        ]
        if not role_requests:
            continue
        for item_index, status in enumerate(work_statuses):
            request_id = role_requests[(responsibility_index + item_index) % len(role_requests)]
            updated_at = base_time - timedelta(hours=responsibility_index * 7 + item_index * 5)
            due_at = updated_at + timedelta(days=2 if status != "Overdue" else -1)
            responsibility_work_rows.append([
                f"WORK-{responsibility_index + 1:02d}-{item_index + 1:02d}",
                responsibility["responsibility_id"],
                request_id,
                responsibility["persona_id"],
                f"Demo {status.casefold()} work for {responsibility['metric_name']}",
                status,
                updated_at,
                due_at,
                "DEMO/SYNTHETIC",
            ])

    # Additional process metrics are derived at runtime from execution records.
    for metric_id, name, formula, unit in [
        ("process-completion-rate", "Process Completion Rate", "Completed executions ÷ Started executions × 100", "%"),
        ("average-process-duration", "Average Completed Process Duration", "Mean duration of completed executions; unfinished executions excluded", "minutes"),
        ("on-time-completion-rate", "On-Time Completion Rate", "Completed executions within configured SLA ÷ Completed executions × 100", "%"),
    ]:
        aggregation = "derived_from_executions"
        numerator_label, denominator_label = _component_labels(formula, aggregation)
        if metric_id == "average-process-duration":
            numerator_label, denominator_label = "Total completed duration (minutes)", "Completed executions"
        definitions.append({"kpi_id": metric_id, "name": name, "description": formula,
                           "definition": formula, "formula": formula,
                           "role_id": "all", "role_name": "All assigned demo roles",
                           "driver": None, "enterprise_linkage": None, "leading_indicator": None,
                           "lagging_result": None, "direction": None,
                           "numerator_label": numerator_label, "denominator_label": denominator_label,
                           "unit": unit, "aggregation": aggregation, "source": "Synthetic process executions",
                           "illustrative": True})

    workbook = Workbook()
    workbook.remove(workbook.active)
    add_sheet(workbook, "Customer_Requests",
              ["request_id", "synthetic_customer_ref", "request_created_at", "request_status", "owner_resource_id", "owner_persona_id", "data_source_type", "value_stream"], request_rows)
    add_sheet(workbook, "Process_Master",
              ["process_id", "process_name", "process_sequence", "predecessor_process_id", "successor_process_id", "is_start", "is_end", "sla_target_minutes", "source", "data_source_type"],
              [[p[0], p[1], p[4], PROCESSES[i - 1][0] if i else None, PROCESSES[i + 1][0] if i < len(PROCESSES) - 1 else None, i == 0, i == len(PROCESSES) - 1, p[5], f"{SOURCE.name} | Consulting Flows", "DEMO/SYNTHETIC workflow"] for i, p in enumerate(PROCESSES)])
    add_sheet(workbook, "Activities_Tasks",
              ["activity_id", "activity_name", "task_id", "task_name", "process_id", "persona_id", "function_id"],
              [[f"ACT-{i:02d}", p[1] + " activity", f"TASK-{i:02d}", p[3], p[0], "assigned per execution", "FUNCTION-OPERATIONS"] for i, p in enumerate(PROCESSES, 1)])
    add_sheet(workbook, "Persona_Resource_Mapping",
              ["resource_id", "email", "display_name", "persona_id", "persona_name", "source_role_sheet", "data_source_type"],
              [[r["resource_id"], r["email"], r["name"], r["persona_id"], r["persona_name"], r["source_role_sheet"], "DEMO/SYNTHETIC assignment"] for r in demo_resources])
    add_sheet(workbook, "Workflow_Definitions",
              ["workflow_id", "sequence", "process_id", "predecessor_process_id", "successor_process_id", "transition_condition", "is_start", "is_end"],
              [["WF-ORDER-DELIVERY", p[4], p[0], PROCESSES[i - 1][0] if i else None, PROCESSES[i + 1][0] if i < len(PROCESSES) - 1 else None, "Always; illustrative demo flow", i == 0, i == len(PROCESSES) - 1] for i, p in enumerate(PROCESSES)])
    execution_headers = ["transaction_id", "customer_request_id", "parent_transaction_id", "process_execution_id", "process_id", "predecessor_process_id", "successor_process_id", "activity_id", "task_id", "workflow_instance_id", "process_sequence", "correlation_id", "process_name", "activity_name", "task_name", "process_execution_status", "task_status", "workflow_status", "execution_outcome", "failure_reason", "retry_count", "function_id", "persona_id", "assigned_resource_id", "assigned_resource_email", "assignment_timestamp", "queue_entry_timestamp", "queue_exit_timestamp", "request_created_timestamp", "process_created_timestamp", "process_start_timestamp", "process_end_timestamp", "actual_duration_minutes", "queue_wait_minutes", "assignment_to_start_minutes", "expected_process_duration_minutes", "sla_target_duration_minutes", "historical_average_minutes", "lower_control_limit_minutes", "upper_control_limit_minutes", "data_source_type", "recorded_delay_reason", "business_date"]
    # Alert metadata is kept in Alert_History; add its reference columns to the execution ledger.
    execution_headers.extend(["alert_id", "alert_severity"])
    add_sheet(workbook, "Process_Executions", execution_headers, execution_rows)
    add_sheet(workbook, "KPI_Definitions",
              ["kpi_id", "kpi_name", "description", "definition", "formula", "persona_id", "persona_name", "driver", "enterprise_linkage", "leading_indicator", "lagging_result", "direction", "measurement_unit", "aggregation_method", "target_value", "target_source", "numerator_label", "denominator_label", "measurement_period", "source", "data_source_type", "illustrative"],
              [[d["kpi_id"], d["name"], d["description"], d["definition"], d["formula"], d["role_id"], d["role_name"], d["driver"], d["enterprise_linkage"], d["leading_indicator"], d["lagging_result"], d["direction"], d["unit"], d["aggregation"], d.get("target_value"), d.get("target_source"), d["numerator_label"], d["denominator_label"], "Weekly", d["source"], "DEMO/SYNTHETIC measurements" if d["illustrative"] else "Reference definition", d["illustrative"]] for d in definitions])
    add_sheet(workbook, "KPI_Measurements",
              ["measurement_id", "kpi_id", "resource_email", "period_start", "period_end", "numerator", "denominator", "unit", "sample_size", "data_source_type", "synthetic"], measurement_rows)
    add_sheet(workbook, "KPI_Observations",
              ["observation_id", "kpi_id", "persona_id", "synthetic_account_id", "synthetic_account_name", "observed_at", "numerator", "denominator", "component_a_label", "component_a_value", "component_b_label", "component_b_value", "result_label", "result_value", "data_source_type", "synthetic"],
              role_observations)
    add_sheet(workbook, "Responsibilities",
              ["responsibility_id", "persona_id", "responsibility", "metric_name", "formula", "target_area", "source"],
              [[item["responsibility_id"], item["persona_id"], item["responsibility"], item["metric_name"],
                item["formula"], item["target_area"],
                f"{SOURCE.name} | Role_Responsibilities | Role {item['role_number']:02d}"] for item in responsibilities])
    add_sheet(workbook, "Responsibility_Work",
              ["work_item_id", "responsibility_id", "customer_request_id", "persona_id", "work_item",
               "status", "updated_at", "due_at", "data_source_type"],
              responsibility_work_rows)
    add_sheet(workbook, "Alert_Rules",
              ["rule_id", "process_id", "rule_type", "sla_target_minutes", "control_limit_method", "control_limit_status", "source"],
              [[f"SLA-{p[0]}", p[0], "SLA", p[5], None, "Not configured; insufficient historical samples for statistical limits", "Illustrative demo SLA; not a J&J-approved target"] for p in PROCESSES])
    add_sheet(workbook, "Alert_History",
              ["alert_id", "process_execution_id", "customer_request_id", "process_id", "persona_id", "resource_id", "alert_type", "severity", "observed_minutes", "threshold_minutes", "resolution_status", "detected_at", "reason"], alert_rows)
    add_sheet(workbook, "Business_Outcomes",
              ["outcome_id", "customer_request_id", "outcome_name", "description", "data_source_type"], outcome_rows)
    dictionary_rows = [
        ["Customer_Requests.request_id", "string", "Required", "Stable synthetic request identifier"],
        ["Customer_Requests.synthetic_customer_ref", "string", "Required", "Non-identifying synthetic customer reference; not a real person"],
        ["Process_Executions.process_execution_id", "string", "Required", "Unique process execution attempt; retries create separate rows"],
        ["Process_Executions.process_start_timestamp", "UTC ISO-8601", "Required", "Process start time"],
        ["Process_Executions.process_end_timestamp", "UTC ISO-8601/null", "Optional", "Null while unfinished; do not treat as completed duration"],
        ["Process_Executions.actual_duration_minutes", "number/null", "Optional", "Recorded only for completed or failed attempts"],
        ["Process_Executions.sla_target_duration_minutes", "number", "Required", "Illustrative SLA threshold; distinct from statistical control limits"],
        ["Process_Executions.lower_control_limit_minutes", "number/null", "Optional", "Not populated: insufficient historical samples"],
        ["Process_Executions.upper_control_limit_minutes", "number/null", "Optional", "Not populated: insufficient historical samples"],
        ["KPI_Definitions.source", "string", "Required", "Workbook/tab lineage for the KPI name and formula"],
        ["KPI_Definitions.illustrative", "boolean", "Required", "True means no approved target/production observation was supplied"],
        ["KPI_Measurements.numerator/denominator", "number", "Required where applicable", "Synthetic weekly inputs; API computes displayed ratios"],
        ["KPI_Measurements.resource_email", "string", "Required", "Demo account scope; never use the editable frontend selection as authorization"],
        ["KPI_Observations.synthetic_account_id", "string", "Required", "Stable synthetic account identifier for a role-specific KPI observation; not a real customer"],
        ["KPI_Observations.numerator/denominator", "number", "Required where applicable", "Raw observation inputs; the authenticated KPI API aggregates these using the source-specific formula"],
        ["KPI_Definitions.target_value", "number/null", "Optional", "Synthetic illustrative target only; not supplied or approved by the source workbook"],
        ["Responsibility_Work.status", "string", "Required", "Illustrative work status linked to a synthetic customer request"],
    ]
    documented_fields = {row[0] for row in dictionary_rows}
    for sheet in workbook.worksheets:
        for cell in sheet[1]:
            field_name = f"{sheet.title}.{cell.value}"
            if field_name in documented_fields:
                continue
            field = str(cell.value).lower()
            if field.endswith("_id") or field.endswith("_email"):
                data_type, meaning = "string", "Stable identifier or reference; see related worksheet for its parent record"
            elif "timestamp" in field or field.endswith("_at") or field.endswith("_date"):
                data_type, meaning = "UTC ISO-8601", "Timestamp/date for this demo record"
            elif "duration" in field or "minutes" in field or field in {"numerator", "denominator", "sample_size", "process_sequence", "retry_count"}:
                data_type, meaning = "number/null", "Synthetic numeric input or calculated duration; null when not yet available"
            elif field in {"is_start", "is_end", "synthetic", "illustrative"}:
                data_type, meaning = "boolean", "Flag describing this synthetic demo record or workflow definition"
            else:
                data_type, meaning = "string", "Synthetic demo attribute; values are illustrative and not production observations"
            dictionary_rows.append([field_name, data_type, "Required unless null", meaning])
            documented_fields.add(field_name)
    add_sheet(workbook, "Data_Dictionary", ["field", "data_type", "required", "meaning_or_relationship"], dictionary_rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(OUTPUT)
    data = {}
    for sheet in workbook.worksheets:
        rows = sheet.iter_rows(values_only=True)
        headers = next(rows)
        data[sheet.title] = [
            dict(zip(headers, row))
            for row in rows
            if any(value is not None for value in row)
        ]
    JSON_OUTPUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    role_count = len({definition["role_id"] for definition in definitions if definition["role_id"] != "all"})
    print(
        f"Created {OUTPUT} and {JSON_OUTPUT} with {len(definitions)} KPI definitions "
        f"across {role_count} sourced roles, {len(measurement_rows)} weekly measurements, "
        f"{len(role_observations)} synthetic observations across {DEMO_ACCOUNT_COUNT_PER_KPI} "
        f"accounts per KPI, {len(responsibilities)} source responsibilities, "
        f"{len(demo_resources)} demo accounts, {len(execution_rows)} process executions, "
        f"and {len(alert_rows)} SLA alerts."
    )


if __name__ == "__main__":
    main()
