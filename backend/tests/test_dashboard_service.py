from backend.app.services.dashboard_service import KPI_LIBRARY, build_dashboard_payload, filter_kpis_for_persona


def test_filter_kpis_for_persona_returns_only_authorized_metrics():
    kpis = [
        {"id": "kpi-1", "persona": "operations", "status": "healthy"},
        {"id": "kpi-2", "persona": "sales", "status": "warning"},
    ]

    result = filter_kpis_for_persona(kpis, "operations")

    assert [item["id"] for item in result] == ["kpi-1"]


def test_build_dashboard_payload_has_expected_panels_and_data():
    payload = build_dashboard_payload("operations")

    assert payload["persona"] == "operations"
    assert payload["status_panel"]
    assert payload["metric_panel"]
    assert payload["responsibility_panel"]
    assert payload["action_panel"]
    assert payload["workflow_panel"]
    assert payload["kpis"]


def test_dashboard_includes_viewer_and_live_series_without_mutating_templates():
    original_value = KPI_LIBRARY[0]["value"]
    payload = build_dashboard_payload("operations", {"name": "Alex", "email": "alex@example.com"})

    assert payload["viewer"] == {"name": "Alex", "email": "alex@example.com"}
    assert payload["updated_at"]
    assert all(len(kpi["series"]) == 12 for kpi in payload["kpis"])
    assert KPI_LIBRARY[0]["value"] == original_value
