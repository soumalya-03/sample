from datetime import date

from backend.app.services.demo_dashboard_service import (
    build_individual_dashboard_payload,
    list_demo_kpis,
    list_demo_process_executions,
    list_demo_responsibilities,
)
from backend.app.services.demo_accounts import DEMO_USERS


def build_dashboard(email: str, name: str, persona_id: str) -> dict:
    return build_individual_dashboard_payload(
        email,
        {"name": name, "email": email},
        persona_id,
    )


def test_demo_dashboard_is_scoped_to_authenticated_resource():
    operations = build_dashboard("admin@local.dev", "Local Admin", "role-09")
    sales = build_dashboard("sales@local.dev", "Jordan Lee", "role-14")

    assert len(operations["requests"]) == 6
    assert len(sales["requests"]) == 6
    assert {item["resource_id"] for item in operations["process_executions"]} == {"RES-OPS-001"}
    assert {item["resource_id"] for item in sales["process_executions"]} == {"RES-SALES-001"}
    assert operations["kpis"][0]["name"] == "Overall SLA Achievement"
    assert sales["kpis"][0]["name"] == "Account Review Completion"


def test_demo_dashboard_calculates_measurements_and_excludes_open_duration():
    payload = build_dashboard("admin@local.dev", "Local Admin", "role-09")
    sla_kpi = next(item for item in payload["kpis"] if item["name"] == "Overall SLA Achievement")
    open_execution = next(item for item in payload["process_executions"] if item["status"] == "In Progress")

    assert sla_kpi["value"] == 93.0
    assert sla_kpi["status"] == "DEMO / illustrative"
    assert open_execution["duration_minutes"] is None
    assert open_execution["elapsed_minutes"] > 0


def test_dashboard_returns_one_coherent_current_workflow_and_can_omit_execution_rows():
    payload = build_dashboard("sales@local.dev", "Jordan Lee", "role-14")
    request_id = payload["workflow_panel"]["request_id"]
    steps = payload["workflow_panel"]["items"]

    assert request_id
    assert [item["status"] for item in steps] == ["Completed", "Completed", "In Progress", "Pending"]
    assert len({item["step"] for item in steps}) == 4

    summary = build_individual_dashboard_payload(
        "sales@local.dev",
        {"name": "Jordan Lee", "email": "sales@local.dev"},
        "role-14",
        include_process_executions=False,
    )
    assert summary["process_executions"] == []


def test_failed_attempt_retry_and_sla_alerts_remain_traceable():
    payload = build_dashboard("admin@local.dev", "Local Admin", "role-09")
    failed = next(item for item in payload["process_executions"] if item["outcome"] == "Failed")
    retry = next(
        item for item in payload["process_executions"]
        if item["customer_request_id"] == failed["customer_request_id"]
        and item["process_id"] == failed["process_id"]
        and item["retry_count"] == 1
    )
    execution_ids = {item["process_execution_id"] for item in payload["process_executions"]}

    assert failed["process_execution_id"] != retry["process_execution_id"]
    assert retry["outcome"] == "Completed"
    assert all(alert["process_execution_id"] in execution_ids for alert in payload["alerts"])


def test_role_14_kpis_use_source_formulas_and_individual_calculations():
    kpis = list_demo_kpis("sales@local.dev", "role-14", "weekly", record_limit=2)
    by_id = {item["kpi_id"]: item for item in kpis}
    account_review = by_id["role-14-account-review-completion"]
    forecast_accuracy = by_id["role-14-forecast-accuracy"]
    role14_kpis = [item for item in kpis if item["kpi_id"].startswith("role-14-")]

    assert len(role14_kpis) == 7
    assert len({item["formula"] for item in role14_kpis}) == 7
    assert all(item["total_observation_count"] == 150 for item in role14_kpis)
    assert all(item["data_available"] and item["records"] for item in role14_kpis)
    assert account_review["formula"] == "Completed account reviews ÷ Planned account reviews"
    assert account_review["numerator_label"] == "Completed account reviews"
    assert account_review["denominator_label"] == "Planned account reviews"
    assert account_review["current_value"] == round(
        account_review["numerator"] / account_review["denominator"] * 100, 2
    )
    assert account_review["target"] == 90
    assert account_review["target_source"].startswith("Synthetic demo target")
    assert account_review["status"] == "Below target (illustrative)"
    assert account_review["total_observation_count"] == 150
    assert account_review["observation_count"] == 20
    assert len(account_review["records"]) == 2
    assert account_review["team_average"] is not None
    assert len(account_review["trend_series"]) >= 2
    assert account_review["data_source_detail"].startswith("Authenticated FastAPI API")
    assert account_review["records"][0]["account_name"].startswith("Synthetic Sales Rep Account")

    assert forecast_accuracy["formula"].startswith("1 − ABS(")
    assert forecast_accuracy["current_value"] == round(
        (1 - forecast_accuracy["numerator"] / forecast_accuracy["denominator"]) * 100, 2
    )
    assert forecast_accuracy["records"][0]["component_a_label"] == "Forecast Volume"
    assert forecast_accuracy["records"][0]["component_b_label"] == "Actual Volume"
    assert forecast_accuracy["current_value"] != round(
        forecast_accuracy["numerator"] / forecast_accuracy["denominator"] * 100, 2
    )


def test_role_14_synthetic_observations_support_all_periods():
    expected_period_counts = {"daily": 2, "weekly": 20}
    for period in ("daily", "weekly", "monthly", "quarterly", "yearly"):
        kpis = list_demo_kpis("sales@local.dev", "role-14", period)
        account_review = next(item for item in kpis if item["kpi_id"] == "role-14-account-review-completion")
        assert account_review["data_available"] is True
        assert account_review["sample_size"] >= expected_period_counts.get(period, 5)
        assert account_review["period"] == period.title()


def test_kpi_observation_pagination_returns_distinct_source_rows():
    first_page = list_demo_kpis("sales@local.dev", "role-14", "weekly", record_limit=2, record_offset=0)
    second_page = list_demo_kpis("sales@local.dev", "role-14", "weekly", record_limit=2, record_offset=2)
    first_records = first_page[0]["records"]
    second_records = second_page[0]["records"]

    assert len(first_records) == len(second_records) == 2
    assert {row["observation_id"] for row in first_records}.isdisjoint(
        row["observation_id"] for row in second_records
    )


def test_role14_responsibilities_use_source_names_and_filtered_work_counts():
    payload = list_demo_responsibilities("role-14")
    assert payload is not None
    responsibilities = payload["responsibilities"]

    assert len(responsibilities) == 7
    assert responsibilities[0]["responsibility"] == "Manage customer accounts and relationships."
    assert responsibilities[0]["metric_name"] == "Account Review Completion"
    assert responsibilities[0]["status_counts"] == {
        "In Progress": 1,
        "Pending": 1,
        "Completed": 1,
        "Blocked": 1,
        "Overdue": 1,
    }

    filtered = list_demo_responsibilities("role-14", status="Overdue")
    assert filtered is not None
    assert sum(item["work_item_count"] for item in filtered["responsibilities"]) == 7
    assert all(row["status"] == "Overdue" for item in filtered["responsibilities"] for row in item["work_items"])


def test_process_execution_filters_are_applied_before_pagination_and_account_scoped():
    payload = list_demo_process_executions(
        "sales@local.dev",
        status="In Progress",
        search="delivery",
        limit=2,
    )

    assert payload["total"] > 0
    assert len(payload["items"]) <= 2
    assert all(row["status"] == "In Progress" and row["process_name"] == "Delivery" for row in payload["items"])
    assert all(row["resource_id"] == "RES-SALES-001" for row in payload["items"])

    admin = list_demo_process_executions("admin@local.dev", status="In Progress")
    assert all(row["resource_id"] == "RES-OPS-001" for row in admin["items"])

    matching = list_demo_process_executions(
        "sales@local.dev",
        process="delivery",
        date_from=date.fromisoformat(payload["items"][0]["started_at"][:10]),
        date_to=date.fromisoformat(payload["items"][0]["started_at"][:10]),
    )
    assert matching["total"] == 1
    assert matching["items"][0]["process_name"] == "Delivery"


def test_all_source_roles_have_role_scoped_kpis_and_synthetic_accounts():
    assert len(DEMO_USERS) == 17
    assert {user["persona_id"] for user in DEMO_USERS} == {
        f"role-{role_number:02d}" for role_number in range(1, 18)
    }

    for role_number in range(1, 17):
        role_id = f"role-{role_number:02d}"
        email = f"role{role_number:02d}@local.dev"
        kpis = list_demo_kpis(email, role_id, "weekly", record_limit=1)
        source_kpis = [item for item in kpis if item["kpi_id"].startswith(f"{role_id}-")]
        assert source_kpis, f"No source KPI data for {role_id}"
        assert all(item["data_available"] and item["total_observation_count"] == 150 for item in source_kpis)
        assert all(len(item["records"]) == 1 for item in source_kpis)

        responsibilities = list_demo_responsibilities(role_id)
        assert responsibilities and responsibilities["responsibilities"]
        assert all(item["work_item_count"] == 5 for item in responsibilities["responsibilities"])


def test_role17_has_a_demo_account_but_no_invented_source_role_kpis():
    payload = list_demo_kpis("role17@local.dev", "role-17", "weekly")

    assert payload
    assert all(item["kpi_id"] in {
        "process-completion-rate",
        "average-process-duration",
        "on-time-completion-rate",
    } for item in payload)
    assert list_demo_responsibilities("role-17")["responsibilities"] == []
