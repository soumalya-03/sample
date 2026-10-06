# Dashboard Project: Short Explanation

## What happens when someone signs in

1. The React login page collects the selected category/persona and the username/password.
2. FastAPI checks the username/password against its local SQLite user database.
3. For this demo, the backend assigns `admin@local.dev` to Role 09, Operations Manager, and `sales@local.dev` to Role 14, Sales Rep. Other accounts have no dashboard assignment. Category is only a demo selection; it does not control access.
4. FastAPI returns a signed login token. The browser sends that token with its dashboard request.
5. The dashboard API checks the token and account assignment, then filters KPI measurements, requests, execution records, and alerts to that account.
6. React displays the returned results in Overview, Customer Metrics, Alerts, and Workflows.

Demo logins: `admin@local.dev` / `local-dev`; `sales@local.dev` / `local-sales`.

## What came from the supplied Excel file

`Medical_Device_Business_Services_Inc_Mentor_08_09_2026.xlsx` supplies KPI names and formula descriptions from its role-specific sheets. The Operations Manager and Sales Rep sheets provide the KPI definitions currently shown for the two demo accounts. Its process documentation informed the vocabulary for the example order journey.

The source file does **not** contain the demo users' actual KPI results, process execution history, alert events, or approved SLA thresholds.

## What was generated for the demo

`data/demo_process_kpi_data.xlsx` is produced by `backend/scripts/generate_demo_process_kpi_data.py`. It contains synthetic weekly KPI inputs, 12 example requests, process execution history, one retry example, and alert records. Names, measurements, timestamps, statuses, durations, sample sizes, account-to-role assignments, and thresholds in this dataset are illustrative only. They are not J&J production information or approved employee scores.

The example process flow has four steps: Capture Order, Validate Order, Submit Order, and Delivery. The flow and its execution records are simplified synthetic examples, not confirmed production workflow rules.

## How KPIs and alerts are calculated

The backend calculates a ratio as `numerator / denominator × 100`, an average as `numerator / denominator`, and a count from its synthetic numerator. It also calculates three process metrics from the example execution records: completion rate, average duration for completed executions, and on-time completion rate. Unfinished processes show elapsed time separately and are excluded from completed-duration averages.

Alerts are **not** taken from the supplied Excel. The generator creates them when an example process duration, or the elapsed time for an unfinished example, exceeds that process's illustrative SLA. It stores an example alert ID, severity, observed time, threshold, status, and linked execution ID. These are static synthetic alerts, not live monitoring. Statistical control limits are not configured because there is no validated historical execution data.

## Technology used

- **Frontend:** React, TypeScript, and Vite; small trend charts are drawn with SVG.
- **Backend:** Python and FastAPI provide login and dashboard APIs.
- **Authentication/data storage:** SQLAlchemy and SQLite store local demo accounts; signed tokens protect the dashboard API.
- **Excel processing:** `openpyxl` reads the source workbook and creates the generated demo workbook.
- **Tests:** pytest checks KPI calculations, unfinished work, retries, alert links, and account separation.

## Short version to explain

“This is a working dashboard prototype. The supplied workbook gives us role KPI names and formula descriptions. Because it has no actual employee performance or process history, the displayed scores, requests, process runs, SLA thresholds, and alerts are synthetic examples. The API scopes those examples to two demo accounts. It is not connected to personal email, corporate identity, or live J&J systems.”
