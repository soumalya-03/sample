import { useEffect, useMemo, useState } from 'react';
import { CATEGORIES, PERSONAS } from './config/loginOptions';
import EmailDiscoveryPortal from './EmailDiscoveryPortal';

type User = {
  user_id?: number;
  email: string;
  name: string;
  role?: string;
  persona_id?: string;
  designation?: string;
  access_token: string;
};

type Kpi = {
  id: string;
  name: string;
  value: number;
  target?: number;
  unit?: string;
  status?: string;
  description?: string;
  category?: string;
  period?: string;
  source?: string;
  sample_size?: number;
  series?: { time: string; value: number }[];
};

type KpiPeriod = 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';

type KpiSummary = {
  kpi_id: string;
  kpi_name: string;
  name: string;
  value: number | null;
  target: number | null;
  unit?: string;
  status: string;
  description?: string;
  formula?: string;
  period: string;
  source?: string;
  sample_size: number;
  total_observation_count: number;
  data_available: boolean;
  availability_message: string | null;
};

type KpiDetail = {
  kpi_id: string;
  kpi_name: string;
  description: string | null;
  definition: string | null;
  formula: string | null;
  unit: string | null;
  current_value: number | null;
  target: number | null;
  target_source: string | null;
  team_average: number | null;
  team_average_label: string | null;
  team_average_variance: number | null;
  team_average_distance: number | null;
  trend_series: { time: string; value: number }[];
  variance_to_target: number | null;
  status: string;
  trend: string;
  numerator: number | null;
  denominator: number | null;
  components: { label: string; value: number | null; unit?: string; component: string }[];
  period: string;
  data_available: boolean;
  availability_message: string | null;
  observation_count: number;
  total_observation_count: number;
  records: {
    observation_id: string;
    account_name: string;
    account_id: string;
    observed_at: string;
    component_a_label: string;
    component_a_value: number;
    component_b_label: string;
    component_b_value: number;
    result_label: string;
    result_value: number;
  }[];
  data_source_detail: string;
  api_endpoint: string;
  viewer_name: string;
  persona: string;
  driver: string | null;
  enterprise_linkage: string | null;
  function: string | null;
  process: string | null;
  activity: string | null;
  task: string | null;
  data_source: string;
  source: string | null;
  last_updated: string;
};

type ProcessExecution = {
  process_execution_id: string;
  customer_request_id: string;
  process_name: string;
  activity_name: string;
  task_name: string;
  process_sequence: number;
  status: string;
  started_at: string;
  duration_minutes: number | null;
  elapsed_minutes: number | null;
  sla_target_minutes: number;
  retry_count: number;
  failure_reason: string | null;
  alert_id: string | null;
};

type DashboardAlert = {
  alert_id: string;
  process_execution_id: string;
  customer_request_id: string;
  alert_type: string;
  severity: string;
  observed_minutes: number;
  threshold_minutes: number;
  resolution_status: string;
  detected_at: string;
  reason: string;
};

type ResponsibilityWorkItem = {
  work_item_id: string;
  responsibility_id: string;
  customer_request_id: string;
  work_item: string;
  status: string;
  updated_at: string;
  due_at: string;
  responsibility?: string;
};

type Responsibility = {
  responsibility_id: string;
  responsibility: string;
  metric_name: string;
  formula: string;
  target_area: string;
  status_counts: Record<string, number>;
  work_item_count: number;
  work_items: ResponsibilityWorkItem[];
};

type DashboardView = 'overview' | 'metrics' | 'kpi-detail' | 'responsibilities' | 'responsibility-detail' | 'mail-discovery' | 'alerts' | 'workflows';

const KPI_PERIODS: KpiPeriod[] = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly'];

function getInitialRoute(): { view: DashboardView; kpiId: string | null; responsibilityId: string | null; period: KpiPeriod } {
  const url = new URL(window.location.href);
  const pathMatch = url.pathname.match(/^\/kpis\/([^/]+)\/?$/);
  const responsibilityMatch = url.pathname.match(/^\/responsibilities\/([^/]+)\/?$/);
  const requestedPeriod = url.searchParams.get('period')?.toLowerCase();
  const period = KPI_PERIODS.find((item) => item === requestedPeriod) ?? 'weekly';
  const requestedView = url.searchParams.get('view');
  return {
    view: pathMatch
      ? 'kpi-detail'
      : responsibilityMatch
        ? 'responsibility-detail'
        : requestedView === 'metrics'
          ? 'metrics'
          : requestedView === 'responsibilities'
            ? 'responsibilities'
            : requestedView === 'mail-discovery'
              ? 'mail-discovery'
              : 'overview',
    kpiId: pathMatch ? decodeURIComponent(pathMatch[1]) : null,
    responsibilityId: responsibilityMatch ? decodeURIComponent(responsibilityMatch[1]) : null,
    period,
  };
}

function formatKpiValue(value: number | null, unit?: string | null): string {
  if (value === null) return 'Not available';
  const formatted = value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return unit ? `${formatted} ${unit}` : formatted;
}

type DashboardResponse = {
  persona: string;
  viewer: { name: string; email: string; designation?: string };
  updated_at: number;
  data_source?: string;
  status_panel?: { title: string; summary: string; items: { label: string; value: string | number; status_filter?: string }[] };
  metric_panel?: { title: string; items: { label: string; value: number | string; unit?: string; status?: string }[] };
  responsibility_panel?: { title: string; items: Responsibility[] };
  action_panel?: { title: string; items: { title: string; priority: string; kpi: string }[] };
  workflow_panel?: { title: string; request_id?: string | null; items: { step: string; status: string }[] };
  kpis?: Kpi[];
  process_executions?: ProcessExecution[];
  alerts?: DashboardAlert[];
  personas?: string[];
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? (window.location.port === '5173' ? 'http://localhost:8000' : window.location.origin);
const STORAGE_KEY = 'jj-dashboard-user';

function authHeaders(user: User): HeadersInit {
  return { Authorization: `Bearer ${user.access_token}` };
}

async function apiFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const message = await response.text();
    let detail = message;
    try {
      detail = JSON.parse(message).detail || message;
    } catch { /* Non-JSON error responses use their text body. */ }
    throw new Error(detail || 'Request failed');
  }

  return response.json() as Promise<T>;
}

function TrendChart({ series, unit }: { series: { time: string; value: number }[]; unit?: string | null }) {
  const values = series;
  if (!values.length) return <div className="trend-empty">Trend data not available for this period</div>;
  const minimum = Math.min(...values.map((point) => point.value));
  const maximum = Math.max(...values.map((point) => point.value));
  const range = maximum - minimum || 1;
  const points = values.map((point, index) => ({
    x: values.length === 1 ? 50 : (index / (values.length - 1)) * 100,
    y: 84 - ((point.value - minimum) / range) * 66,
  }));
  const line = points.map((point) => `${point.x},${point.y}`).join(' ');
  const area = `0,100 ${line} 100,100`;

  return (
    <div className="trend-chart-wrap">
      <svg className="trend-chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={`KPI trend in ${unit ?? 'selected units'}`}>
        <polygon className="trend-area" points={area} />
        <polyline className="trend-line" points={line} />
        <circle className="trend-point" cx={points[points.length - 1].x} cy={points[points.length - 1].y} r="2.4" />
      </svg>
      <div className="trend-range"><span>{values[0].time}</span><span>{values[values.length - 1].time}</span></div>
    </div>
  );
}

export default function App() {
  const initialRoute = getInitialRoute();
  const [user, setUser] = useState<User | null>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      const parsed = saved ? JSON.parse(saved) as User : null;
      if (parsed?.access_token) return parsed;
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
    return null;
  });
  const [category, setCategory] = useState('');
  const [persona, setPersona] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [processSearch, setProcessSearch] = useState('');
  const [executionSearch, setExecutionSearch] = useState('');
  const [processFilter, setProcessFilter] = useState('');
  const [executionDateFrom, setExecutionDateFrom] = useState('');
  const [executionDateTo, setExecutionDateTo] = useState('');
  const [executionStatus, setExecutionStatus] = useState('');
  const [processExecutions, setProcessExecutions] = useState<ProcessExecution[]>([]);
  const [processExecutionTotal, setProcessExecutionTotal] = useState(0);
  const [processExecutionsLoading, setProcessExecutionsLoading] = useState(false);
  const [processExecutionsError, setProcessExecutionsError] = useState('');
  const [workStatusFilter, setWorkStatusFilter] = useState('');
  const [filteredWorkItems, setFilteredWorkItems] = useState<ResponsibilityWorkItem[]>([]);
  const [filteredWorkLoading, setFilteredWorkLoading] = useState(false);
  const [selectedResponsibilityId, setSelectedResponsibilityId] = useState<string | null>(initialRoute.responsibilityId);
  const [responsibilityDetail, setResponsibilityDetail] = useState<Responsibility | null>(null);
  const [responsibilityLoading, setResponsibilityLoading] = useState(false);
  const [responsibilityError, setResponsibilityError] = useState('');
  const [activeView, setActiveView] = useState<DashboardView>(initialRoute.view);
  const [selectedKpiId, setSelectedKpiId] = useState<string | null>(initialRoute.kpiId);
  const [metricsPeriod, setMetricsPeriod] = useState<KpiPeriod>(initialRoute.period);
  const [metricKpis, setMetricKpis] = useState<KpiSummary[]>([]);
  const [kpiListLoading, setKpiListLoading] = useState(false);
  const [kpiListError, setKpiListError] = useState('');
  const [kpiDetail, setKpiDetail] = useState<KpiDetail | null>(null);
  const [kpiDetailLoading, setKpiDetailLoading] = useState(false);
  const [kpiDetailError, setKpiDetailError] = useState('');
  const [kpiRecordsLoading, setKpiRecordsLoading] = useState(false);
  const [kpiRecordsError, setKpiRecordsError] = useState('');

  useEffect(() => {
    if (!user) return;
    void fetchDashboard(user, true);
  }, [user]);

  useEffect(() => {
    const syncRoute = () => {
      const route = getInitialRoute();
      setActiveView(route.view);
      setSelectedKpiId(route.kpiId);
      setSelectedResponsibilityId(route.responsibilityId);
      setMetricsPeriod(route.period);
    };
    window.addEventListener('popstate', syncRoute);
    return () => window.removeEventListener('popstate', syncRoute);
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => setExecutionSearch(processSearch), 250);
    return () => window.clearTimeout(timeout);
  }, [processSearch]);

  useEffect(() => {
    if (!user || activeView !== 'overview' || !workStatusFilter) {
      setFilteredWorkItems([]);
      return;
    }
    let current = true;
    setFilteredWorkLoading(true);
    void apiFetch<{ responsibilities: Responsibility[] }>(
      `/api/dashboard/responsibilities?status=${encodeURIComponent(workStatusFilter)}`,
      { headers: authHeaders(user) },
    ).then((payload) => {
      if (current) {
        setFilteredWorkItems(payload.responsibilities.flatMap((item) =>
          item.work_items.map((workItem) => ({ ...workItem, responsibility: item.responsibility } as ResponsibilityWorkItem & { responsibility: string })),
        ));
      }
    }).catch((fetchError: unknown) => {
      if (current) setError(fetchError instanceof Error ? fetchError.message : 'Filtered work could not be loaded.');
    }).finally(() => {
      if (current) setFilteredWorkLoading(false);
    });
    return () => { current = false; };
  }, [user, activeView, workStatusFilter]);

  useEffect(() => {
    if (!user || activeView !== 'responsibility-detail' || !selectedResponsibilityId) return;
    let current = true;
    setResponsibilityDetail(null);
    setResponsibilityLoading(true);
    setResponsibilityError('');
    const query = new URLSearchParams();
    if (workStatusFilter) query.set('status', workStatusFilter);
    const queryString = query.toString();
    void apiFetch<{ responsibilities: Responsibility[] }>(
      `/api/dashboard/responsibilities/${encodeURIComponent(selectedResponsibilityId)}${queryString ? `?${queryString}` : ''}`,
      { headers: authHeaders(user) },
    ).then((payload) => {
      if (current) setResponsibilityDetail(payload.responsibilities[0] ?? null);
    }).catch((fetchError: unknown) => {
      if (current) setResponsibilityError(fetchError instanceof Error ? fetchError.message : 'Responsibility details could not be loaded.');
    }).finally(() => {
      if (current) setResponsibilityLoading(false);
    });
    return () => { current = false; };
  }, [user, activeView, selectedResponsibilityId, workStatusFilter]);

  useEffect(() => {
    if (!user || activeView !== 'workflows') return;
    let current = true;
    setProcessExecutionsLoading(true);
    setProcessExecutions([]);
    setProcessExecutionTotal(0);
    setProcessExecutionsError('');
    const query = new URLSearchParams({ limit: '25', offset: '0' });
    if (executionStatus) query.set('status', executionStatus);
    if (executionSearch.trim()) query.set('search', executionSearch.trim());
    if (processFilter.trim()) query.set('process', processFilter.trim());
    if (executionDateFrom) query.set('date_from', executionDateFrom);
    if (executionDateTo) query.set('date_to', executionDateTo);
    void apiFetch<{ items: ProcessExecution[]; total: number }>(
      `/api/dashboard/process-executions?${query.toString()}`,
      { headers: authHeaders(user) },
    ).then((payload) => {
      if (current) {
        setProcessExecutions(payload.items);
        setProcessExecutionTotal(payload.total);
      }
    }).catch((fetchError: unknown) => {
      if (current) setProcessExecutionsError(fetchError instanceof Error ? fetchError.message : 'Filtered process history could not be loaded.');
    }).finally(() => {
      if (current) setProcessExecutionsLoading(false);
    });
    return () => { current = false; };
  }, [user, activeView, executionSearch, executionStatus, processFilter, executionDateFrom, executionDateTo]);

  useEffect(() => {
    if (!user || activeView !== 'metrics') return;
    let current = true;
    setKpiListLoading(true);
    setKpiListError('');
    void apiFetch<{ kpis: KpiSummary[] }>(`/api/kpis?period=${metricsPeriod}`, {
      headers: { Authorization: `Bearer ${user.access_token}` },
    }).then((payload) => {
      if (current) setMetricKpis(payload.kpis);
    }).catch((fetchError: unknown) => {
      if (current) setKpiListError(fetchError instanceof Error ? fetchError.message : 'KPI metrics could not be loaded.');
    }).finally(() => {
      if (current) setKpiListLoading(false);
    });
    return () => { current = false; };
  }, [user, activeView, metricsPeriod]);

  useEffect(() => {
    if (!user || activeView !== 'kpi-detail' || !selectedKpiId) return;
    let current = true;
    setKpiDetail(null);
    setKpiDetailLoading(true);
    setKpiDetailError('');
    void apiFetch<KpiDetail>(`/api/kpis/${encodeURIComponent(selectedKpiId)}/details?period=${metricsPeriod}&limit=1&offset=0`, {
      headers: { Authorization: `Bearer ${user.access_token}` },
    }).then((detail) => {
      if (current) setKpiDetail(detail);
    }).catch((fetchError: unknown) => {
      if (current) setKpiDetailError(fetchError instanceof Error ? fetchError.message : 'KPI details could not be loaded.');
    }).finally(() => {
      if (current) setKpiDetailLoading(false);
    });
    setKpiRecordsError('');
    return () => { current = false; };
  }, [user, activeView, selectedKpiId, metricsPeriod]);

  const fetchDashboard = async (activeUser: User, showLoading = false) => {
    try {
      if (showLoading) setDashboardLoading(true);
      const payload = await apiFetch<DashboardResponse>('/api/dashboard/persona?include_process_executions=false', {
        headers: { Authorization: `Bearer ${activeUser.access_token}` },
      });
      setDashboard(payload);
      setMetricKpis((payload.kpis ?? []).map((kpi) => ({
        kpi_id: kpi.id,
        kpi_name: kpi.name,
        name: kpi.name,
        value: kpi.value,
        target: kpi.target ?? null,
        unit: kpi.unit,
        status: kpi.status ?? 'DEMO / illustrative',
        description: kpi.description,
        period: kpi.period ?? 'Weekly',
        source: kpi.source,
        sample_size: kpi.sample_size ?? 0,
        total_observation_count: kpi.sample_size ?? 0,
        data_available: true,
        availability_message: null,
      })));
    } catch (fetchError) {
      console.error(fetchError);
      if (fetchError instanceof Error && fetchError.message.includes('Sign in')) handleLogout();
      else setError('The dashboard could not load KPI metrics.');
    } finally {
      if (showLoading) setDashboardLoading(false);
    }
  };

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!category || !persona || !username.trim() || !password) {
      setError('Complete all four fields to continue.');
      return;
    }
    setIsLoading(true);
    setError('');

    try {
      const authUser = await apiFetch<User>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: username.trim(), password, persona_id: persona }),
      });

      const selectedDesignation = PERSONAS.find((item) => item.value === persona)?.label;
      const nextUser = {
        ...authUser,
        email: authUser.email ?? username.trim(),
        designation: authUser.designation ?? selectedDesignation ?? persona,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(nextUser));
      setUser(nextUser);
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : 'Login failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePersonaChange = (selectedPersona: string) => {
    setPersona(selectedPersona);
    const demoAccount = PERSONAS.find((item) => item.value === selectedPersona);
    setUsername(demoAccount?.demoEmail ?? '');
    setPassword(demoAccount?.demoPassword ?? '');
    setError('');
  };

  const navigateView = (view: DashboardView) => {
    if (view === 'kpi-detail' || view === 'responsibility-detail') return;
    const route = view === 'metrics' ? `/?view=metrics&period=${metricsPeriod}` : view === 'responsibilities' ? '/?view=responsibilities' : view === 'mail-discovery' ? '/?view=mail-discovery' : '/';
    window.history.pushState({}, '', route);
    setSelectedKpiId(null);
    setSelectedResponsibilityId(null);
    setWorkStatusFilter('');
    setActiveView(view);
  };

  const openKpiDetail = (kpiId: string) => {
    window.history.pushState({}, '', `/kpis/${encodeURIComponent(kpiId)}?period=${metricsPeriod}`);
    setSelectedKpiId(kpiId);
    setActiveView('kpi-detail');
  };

  const openResponsibilityDetail = (responsibilityId: string) => {
    window.history.pushState({}, '', `/responsibilities/${encodeURIComponent(responsibilityId)}`);
    setSelectedResponsibilityId(responsibilityId);
    setWorkStatusFilter('');
    setActiveView('responsibility-detail');
  };

  const changeMetricsPeriod = (period: KpiPeriod) => {
    const route = activeView === 'kpi-detail' && selectedKpiId
      ? `/kpis/${encodeURIComponent(selectedKpiId)}?period=${period}`
      : `/?view=metrics&period=${period}`;
    window.history.replaceState({}, '', route);
    setMetricsPeriod(period);
  };

  const loadMoreKpiRecords = async () => {
    if (!user || !selectedKpiId || !kpiDetail || kpiRecordsLoading) return;
    setKpiRecordsLoading(true);
    setKpiRecordsError('');
    const offset = kpiDetail.records.length;
    try {
      const response = await apiFetch<KpiDetail>(
        `/api/kpis/${encodeURIComponent(selectedKpiId)}/details?period=${metricsPeriod}&limit=10&offset=${offset}`,
        { headers: { Authorization: `Bearer ${user.access_token}` } },
      );
      setKpiDetail((current) => current
        ? { ...current, records: [...current.records, ...response.records] }
        : current);
    } catch (loadError) {
      setKpiRecordsError(loadError instanceof Error ? loadError.message : 'More KPI records could not be loaded.');
    } finally {
      setKpiRecordsLoading(false);
    }
  };

  const loadMoreProcessExecutions = async () => {
    if (!user || processExecutionsLoading) return;
    setProcessExecutionsLoading(true);
    setProcessExecutionsError('');
    const query = new URLSearchParams({ limit: '25', offset: String(processExecutions.length) });
    if (executionStatus) query.set('status', executionStatus);
    if (executionSearch.trim()) query.set('search', executionSearch.trim());
    if (processFilter.trim()) query.set('process', processFilter.trim());
    if (executionDateFrom) query.set('date_from', executionDateFrom);
    if (executionDateTo) query.set('date_to', executionDateTo);
    try {
      const payload = await apiFetch<{ items: ProcessExecution[]; total: number }>(
        `/api/dashboard/process-executions?${query.toString()}`,
        { headers: authHeaders(user) },
      );
      setProcessExecutions((current) => [...current, ...payload.items]);
      setProcessExecutionTotal(payload.total);
    } catch (loadError) {
      setProcessExecutionsError(loadError instanceof Error ? loadError.message : 'More process history could not be loaded.');
    } finally {
      setProcessExecutionsLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
    setDashboard(null);
    setCategory('');
    setPersona('');
    setUsername('');
    setPassword('');
    setShowPassword(false);
    setError('');
    setKpiDetail(null);
    setSelectedKpiId(null);
    setActiveView('overview');
    setMetricsPeriod('weekly');
    window.history.replaceState({}, '', '/');
  };

  const visibleDashboard = useMemo(() => dashboard ?? null, [dashboard]);
  const viewerName = visibleDashboard?.viewer.name ?? user?.name ?? 'Team member';
  const hour = new Date().getHours();
  const greeting = hour >= 5 && hour < 12
    ? 'Good morning'
    : hour < 17 && hour >= 12
      ? 'Good afternoon'
      : hour < 21 && hour >= 17
        ? 'Good evening'
        : 'Good night';

  if (!user) {
    return (
      <div className="auth-shell">
        <header className="auth-header">
          <div className="identity-mark" aria-hidden="true">J&amp;J</div>
          <div className="identity-copy">
            <strong>J&amp;J KPI Dashboard</strong>
            <span>Business Performance &amp; Insights</span>
          </div>
          <span className="environment-badge">DEMO</span>
        </header>

        <main className="auth-main">
          <section className="auth-card" aria-labelledby="login-title">
            <div className="form-kicker">Secure workspace access</div>
            <h1 id="login-title">Welcome back</h1>
            <p className="auth-description">Sign in to access your role-specific dashboard.</p>

            <form onSubmit={handleLogin} className="auth-form" noValidate>
              <label>
                Category
                <select value={category} onChange={(event) => setCategory(event.target.value)} required>
                  <option value="" disabled>Select category</option>
                  {CATEGORIES.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
                <small className="field-note">Category is for demo selection; your persona determines the dashboard.</small>
              </label>

              <label>
                Persona
                <select value={persona} onChange={(event) => handlePersonaChange(event.target.value)} required>
                  <option value="" disabled>Select your persona</option>
                  {PERSONAS.map((item) => (
                    <option key={item.value} value={item.value} disabled={!item.defined}>
                      {item.label}
                    </option>
                  ))}
                </select>
                <small className="field-note">Selecting a persona fills its matching demo username and password.</small>
              </label>

              <label>
                Username
                <input
                  type="text"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="Enter your username"
                  autoComplete="username"
                  required
                />
              </label>

              <label>
                Password
                <span className="password-field">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Enter your password"
                    autoComplete="current-password"
                    required
                  />
                  <button
                    className="password-toggle"
                    type="button"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    aria-pressed={showPassword}
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </span>
              </label>

              {error && <div className="error-banner" role="alert">{error}</div>}
              <button className="sign-in-button" type="submit" disabled={isLoading}>
                {isLoading ? <><span className="button-spinner" aria-hidden="true" />Signing in</> : <>Sign in <span aria-hidden="true">→</span></>}
              </button>
            </form>

            <p className="selection-note">Demo sign-in accounts are available for all 17 role selections. Source KPI definitions are available for Roles 01–16.</p>
          </section>
          <footer className="auth-footer">DEMO ENVIRONMENT <span aria-hidden="true">·</span> Not configured for corporate identity sign-in</footer>
        </main>
      </div>
    );
  }

  const statusItems = visibleDashboard?.status_panel?.items ?? [];
  const responsibilities = visibleDashboard?.responsibility_panel?.items ?? [];
  const workflowSteps = visibleDashboard?.workflow_panel?.items ?? [];
  const kpis = visibleDashboard?.kpis ?? [];
  const alerts = visibleDashboard?.alerts ?? [];
  const executionsByRequest = new Map<string, ProcessExecution[]>();
  for (const execution of processExecutions) {
    const requestExecutions = executionsByRequest.get(execution.customer_request_id) ?? [];
    requestExecutions.push(execution);
    executionsByRequest.set(execution.customer_request_id, requestExecutions);
  }
  const viewTitles: Record<DashboardView, string> = {
    overview: 'overview',
    metrics: 'customer metrics',
    'kpi-detail': 'KPI detail',
    responsibilities: 'responsibilities',
    'responsibility-detail': 'responsibility details',
    'mail-discovery': 'mail discovery',
    alerts: 'alerts',
    workflows: 'workflows',
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand-mark small">J&amp;J</div>
          <div>
            <strong>Business Services</strong>
            <span>KPI Command Center</span>
          </div>
        </div>

        <nav className="nav">
          {(['overview', 'metrics', 'responsibilities', 'alerts', 'workflows'] as const).map((view) => (
            <button
              key={view}
              className={`nav-item${(activeView === view || (view === 'metrics' && activeView === 'kpi-detail') || (view === 'responsibilities' && activeView === 'responsibility-detail')) ? ' active' : ''}`}
              type="button"
              aria-current={activeView === view || (view === 'metrics' && activeView === 'kpi-detail') || (view === 'responsibilities' && activeView === 'responsibility-detail') ? 'page' : undefined}
              onClick={() => navigateView(view)}
            >
              {view === 'metrics' ? 'Customer Metrics' : view[0].toUpperCase() + view.slice(1)}
            </button>
          ))}
        </nav>

        <div className="profile-card">
          <div className="avatar">{(visibleDashboard?.viewer.name ?? user.name).charAt(0).toUpperCase()}</div>
          <div>
            <strong>{visibleDashboard?.viewer.name ?? user.name}</strong>
            <span>{user.designation ?? user.role ?? 'Team member'}</span>
            <span>{visibleDashboard?.viewer.email ?? user.email}</span>
          </div>
        </div>
      </aside>

      <main className="content-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Operational dashboard</p>
            <h2>
              {activeView === 'overview'
                ? `${greeting}, ${viewerName}`
                : activeView === 'kpi-detail'
                  ? viewTitles[activeView]
                  : `${viewerName}'s ${viewTitles[activeView]}`}
            </h2>
            {activeView === 'overview' && <span className="viewer-designation">{visibleDashboard?.viewer.designation ?? user.designation ?? 'Team member'}</span>}
          </div>
          <div className="topbar-actions">
            {(activeView === 'metrics' || activeView === 'kpi-detail') && (
              <label className="period-picker">
                Time period
                <select
                  value={metricsPeriod}
                  onChange={(event) => {
                    const period = KPI_PERIODS.find((item) => item === event.target.value);
                    if (period) changeMetricsPeriod(period);
                  }}
                >
                  {KPI_PERIODS.map((period) => <option key={period} value={period}>{period[0].toUpperCase() + period.slice(1)}</option>)}
                </select>
              </label>
            )}
            <div className="live-status"><span className="live-dot" />{visibleDashboard?.data_source ?? 'DEMO / SYNTHETIC DATA'} <small>{visibleDashboard?.updated_at ? new Date(visibleDashboard.updated_at).toLocaleTimeString() : ''}</small></div>
            <button className="secondary-btn" onClick={handleLogout}>Sign out</button>
          </div>
        </header>

        {error && <div className="error-banner inline">{error}</div>}

        {dashboardLoading ? (
          <div className="loading-panel">Loading KPI data…</div>
        ) : (
          <>
            {activeView === 'overview' && <>
            <section className="status-grid">
              {statusItems.length ? (
                statusItems.map((item) => item.status_filter ? (
                  <button
                    key={item.label}
                    type="button"
                    className={`mini-card status-filter-card${workStatusFilter === item.status_filter ? ' selected' : ''}`}
                    onClick={() => setWorkStatusFilter((current) => current === item.status_filter ? '' : item.status_filter ?? '')}
                  >
                    <span>{item.label}</span><strong>{item.value}</strong>
                  </button>
                ) : (
                  <article key={item.label} className="mini-card"><span>{item.label}</span><strong>{item.value}</strong></article>
                ))
              ) : (
                <div className="empty-state">No status data available for this persona.</div>
              )}
            </section>

            <section className="panel-grid">
              <article className="panel-card wide-panel priority-panel">
                <div className="panel-heading">
                  <div><h3>Priority KPIs</h3><p>Sorted by illustrative target status; thresholds are demo-only.</p></div>
                </div>
                <div className="priority-kpi-list">
                  {kpis.length ? (
                    kpis.map((kpi) => (
                      <button className="priority-kpi-card" key={kpi.id} type="button" onClick={() => openKpiDetail(kpi.id)}>
                        <span><strong>{kpi.name}</strong><small>{kpi.status ?? 'Demo measurement'}</small></span>
                        <strong>{kpi.value.toLocaleString(undefined, { maximumFractionDigits: 2 })} {kpi.unit ?? ''}</strong>
                        <small>{kpi.target === undefined || kpi.target === null ? 'No source target' : `Demo target ${kpi.target} ${kpi.unit ?? ''}`}</small>
                      </button>
                    ))
                  ) : (
                    <div className="empty-state">No KPI metrics available.</div>
                  )}
                </div>
              </article>

              {workStatusFilter && (
                <article className="panel-card wide-panel">
                  <div className="panel-heading"><h3>{workStatusFilter} work</h3><button className="text-button" type="button" onClick={() => setWorkStatusFilter('')}>Clear filter</button></div>
                  {filteredWorkLoading ? <div className="loading-panel">Loading filtered work…</div> : filteredWorkItems.length ? (
                    <div className="work-items-list">
                      {filteredWorkItems.map((item) => (
                        <div className="work-item-row" key={item.work_item_id}>
                          <span><strong>{item.work_item}</strong><small>{item.responsibility} · {item.customer_request_id} · Due {new Date(item.due_at).toLocaleDateString()}</small></span>
                          <em>{item.status}</em>
                        </div>
                      ))}
                    </div>
                  ) : <div className="empty-state">No work items have this status.</div>}
                </article>
              )}

              <article className="panel-card">
                <div className="panel-heading">
                  <div>
                    <h3>{visibleDashboard?.workflow_panel?.title ?? 'Workflow'}</h3>
                    {visibleDashboard?.workflow_panel?.request_id && <p className="panel-description">{visibleDashboard.workflow_panel.request_id}</p>}
                  </div>
                </div>
                <div className="timeline">
                  {workflowSteps.length ? (
                    workflowSteps.map((step) => (
                      <div key={step.step} className="timeline-step">
                        <span className="dot" />
                        <div>
                          <strong>{step.step}</strong>
                          <small>{step.status}</small>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="empty-state">No workflow steps available.</div>
                  )}
                </div>
              </article>
            </section>
            </>}

            {activeView === 'responsibilities' && (
              <section className="panel-card details-panel">
                <div className="panel-heading">
                  <h3>{visibleDashboard?.responsibility_panel?.title ?? 'Responsibilities'}</h3>
                </div>
                <div className="responsibility-list">
                  {responsibilities.length ? (
                    responsibilities.map((item) => (
                      <button key={item.responsibility_id} className="responsibility-card" type="button" onClick={() => openResponsibilityDetail(item.responsibility_id)}>
                        <strong>{item.responsibility}</strong>
                        <small>{item.metric_name} · {item.work_item_count} synthetic work items</small>
                        <span>Pending {item.status_counts.Pending ?? 0} · In progress {item.status_counts['In Progress'] ?? 0} · Overdue {item.status_counts.Overdue ?? 0}</span>
                      </button>
                    ))
                  ) : (
                    <div className="empty-state">No responsibilities configured.</div>
                  )}
                </div>
                <div className="panel-heading" style={{ marginTop: '24px' }}>
                  <div><h3>Mail</h3><p>Discover and review mailbox correspondence linked to this role.</p></div>
                </div>
                <button className="secondary-btn" type="button" onClick={() => navigateView('mail-discovery')}>Open Mail Discovery</button>
              </section>
            )}

            {activeView === 'mail-discovery' && (
              <section className="panel-card details-panel">
                <button className="breadcrumb-button" type="button" onClick={() => navigateView('responsibilities')}><span aria-hidden="true">←</span> Responsibilities</button>
                <EmailDiscoveryPortal />
              </section>
            )}

            {activeView === 'responsibility-detail' && (
              <section className="panel-card details-panel">
                <button className="breadcrumb-button" type="button" onClick={() => navigateView('responsibilities')}><span aria-hidden="true">←</span> Responsibilities</button>
                {responsibilityLoading ? <div className="loading-panel">Loading responsibility…</div> : responsibilityError ? (
                  <div className="error-banner" role="alert">{responsibilityError}</div>
                ) : responsibilityDetail ? (
                  <>
                    <div className="panel-heading"><div><p className="eyebrow">Source: Role_Responsibilities · Role 14</p><h3>{responsibilityDetail.responsibility}</h3><p>{responsibilityDetail.target_area} · {responsibilityDetail.metric_name}</p></div></div>
                    <dl className="definition-list compact-definition"><div><dt>Metric formula</dt><dd>{responsibilityDetail.formula}</dd></div></dl>
                    <div className="responsibility-status-grid">
                      {['Pending', 'In Progress', 'Completed', 'Blocked', 'Overdue'].map((status) => (
                        <button key={status} type="button" className={`mini-card status-filter-card${workStatusFilter === status ? ' selected' : ''}`} onClick={() => setWorkStatusFilter((current) => current === status ? '' : status)}>
                          <span>{status}</span><strong>{responsibilityDetail.status_counts[status] ?? 0}</strong>
                        </button>
                      ))}
                    </div>
                    <h4 className="section-title">Current work</h4>
                    <div className="work-items-list">
                      {responsibilityDetail.work_items.map((item) => (
                        <div className="work-item-row" key={item.work_item_id}>
                          <span><strong>{item.work_item}</strong><small>{item.customer_request_id} · Due {new Date(item.due_at).toLocaleDateString()}</small></span>
                          <em>{item.status}</em>
                        </div>
                      ))}
                      {!responsibilityDetail.work_items.length && <div className="empty-state">No work items match this status.</div>}
                    </div>
                  </>
                ) : <div className="empty-state">Responsibility is not available.</div>}
              </section>
            )}

            {activeView === 'metrics' && <section className="panel-card details-panel">
              <div className="panel-heading">
                <div>
                  <h3>{visibleDashboard?.metric_panel?.title ?? 'Customer metrics'}</h3>
                  <p className="panel-description">Select a KPI to inspect its source definition and calculation.</p>
                </div>
              </div>
              <div className="kpi-list">
                {kpiListLoading ? (
                  <div className="loading-panel">Loading KPI metrics…</div>
                ) : kpiListError ? (
                  <div className="error-banner" role="alert">{kpiListError}</div>
                ) : metricKpis.length ? (
                  metricKpis.map((kpi) => (
                    <article
                      key={kpi.kpi_id}
                      className="kpi-card kpi-card-clickable"
                      role="button"
                      tabIndex={0}
                      aria-label={`View details for ${kpi.kpi_name}`}
                      onClick={() => openKpiDetail(kpi.kpi_id)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          openKpiDetail(kpi.kpi_id);
                        }
                      }}
                    >
                      <div className="kpi-header">
                        <div>
                          <h4>{kpi.kpi_name}</h4>
                          <p>{kpi.description ?? 'No definition is available from the source.'}</p>
                        </div>
                        <span className="status-pill demo">{kpi.status}</span>
                      </div>
                      <div className="kpi-row">
                        <strong>{kpi.value === null ? '—' : kpi.value.toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong>
                        <span>{kpi.unit ?? '%'}</span>
                      </div>
                      <div className="kpi-meta">
                        <span>Target: {kpi.target ?? 'Not supplied'}</span>
                        <span>Period: {kpi.period}</span>
                        <span>Sample size: {kpi.sample_size || 'Not available'}</span>
                        <span>Source: {kpi.source ?? 'Not supplied'}</span>
                      </div>
                      {kpi.availability_message && <p className="period-empty-note">{kpi.availability_message}</p>}
                      <span className="kpi-detail-link">View KPI details <span aria-hidden="true">→</span></span>
                    </article>
                  ))
                ) : (
                  <div className="empty-state">No KPI definitions available for this persona.</div>
                )}
              </div>
            </section>}

            {activeView === 'kpi-detail' && (
              <section className="panel-card details-panel kpi-detail-panel">
                <button className="breadcrumb-button" type="button" onClick={() => navigateView('metrics')}>
                  <span aria-hidden="true">←</span> Customer Metrics
                </button>
                {kpiDetailLoading ? (
                  <div className="loading-panel">Loading KPI details…</div>
                ) : kpiDetailError ? (
                  <div className="error-banner" role="alert">{kpiDetailError}</div>
                ) : kpiDetail ? (
                  <>
                    <div className="kpi-detail-heading">
                      <div>
                        <p className="eyebrow">API · WORKBOOK-BACKED · {kpiDetail.data_source}</p>
                        <h3>{kpiDetail.kpi_name}</h3>
                        <p>{kpiDetail.period} · {kpiDetail.viewer_name}</p>
                      </div>
                      <span className={`status-pill ${kpiDetail.target === null ? 'demo' : ''}`}>{kpiDetail.status}</span>
                    </div>

                    {!kpiDetail.data_available && (
                      <div className="empty-state period-empty-state" role="status">
                        {kpiDetail.availability_message ?? 'Demo data not available for this period'}
                      </div>
                    )}

                    <section className="kpi-summary-cards">
                      <article><span>Current</span><strong>{formatKpiValue(kpiDetail.current_value, kpiDetail.unit)}</strong></article>
                      <article><span>{kpiDetail.target_source ? 'Illustrative demo target' : 'Target'}</span><strong>{kpiDetail.target === null ? 'Not configured' : formatKpiValue(kpiDetail.target, kpiDetail.unit)}</strong>{kpiDetail.variance_to_target !== null && <small>Variance {formatKpiValue(kpiDetail.variance_to_target, kpiDetail.unit)}</small>}</article>
                      <article><span>Team average</span><strong>{kpiDetail.team_average === null ? 'Not available' : formatKpiValue(kpiDetail.team_average, kpiDetail.unit)}</strong><small>{kpiDetail.team_average_label}</small></article>
                    </section>
                    <section className="kpi-detail-section compact-trend-section">
                      <div className="panel-heading"><div><h4>Recent weekly trend</h4><p>{kpiDetail.trend} · {kpiDetail.observation_count} observations in the selected {kpiDetail.period.toLowerCase()} period</p></div></div>
                      <TrendChart series={kpiDetail.trend_series} unit={kpiDetail.unit} />
                    </section>
                    {kpiDetail.team_average_variance !== null && (
                      <p className="kpi-insight">Current period is {formatKpiValue(Math.abs(kpiDetail.team_average_variance), kpiDetail.unit)} {kpiDetail.team_average_variance >= 0 ? 'above' : 'below'} the all-time synthetic team average.</p>
                    )}
                    <section className="kpi-detail-section compact-definition-section">
                      <h4>Definition and calculation</h4>
                      <dl className="definition-list">
                        <div><dt>Definition</dt><dd>{kpiDetail.definition ?? 'No definition supplied by the source.'}</dd></div>
                        <div><dt>Formula</dt><dd>{kpiDetail.formula ?? 'No formula supplied by the source.'}</dd></div>
                        <div><dt>Source</dt><dd>{kpiDetail.source ?? 'No source supplied'}</dd></div>
                        <div><dt>Last updated</dt><dd>{new Date(kpiDetail.last_updated).toLocaleString()} · {kpiDetail.total_observation_count.toLocaleString()} synthetic observations</dd></div>
                        {kpiDetail.target_source && <div><dt>Target note</dt><dd>{kpiDetail.target_source}</dd></div>}
                      </dl>
                    </section>
                  </>
                ) : (
                  <div className="empty-state">Select a KPI from Customer Metrics to view its details.</div>
                )}
              </section>
            )}

            {activeView === 'workflows' && <>
            <section className="panel-card details-panel">
              <div className="panel-heading">
                <div>
                  <h3>Request workflow history</h3>
                  <p>Process executions grouped by synthetic customer request and ordered by configured sequence.</p>
                </div>
              </div>
              <div className="workflow-history">
                {[...executionsByRequest.entries()].map(([requestId, executions]) => (
                  <article key={requestId} className="workflow-request">
                    <h4>{requestId}</h4>
                    <ol>
                      {[...executions].sort((left, right) => left.process_sequence - right.process_sequence).map((execution) => (
                        <li key={execution.process_execution_id}>
                          <span className={`workflow-state ${execution.status.toLowerCase().replace(/\s+/g, '-')}`} />
                          <div>
                            <strong>{execution.process_name}</strong>
                            <small>{execution.status} · {execution.status === 'Pending' ? 'Not started' : execution.duration_minutes === null ? `${execution.elapsed_minutes ?? 0} min elapsed` : `${execution.duration_minutes} min`}</small>
                            {execution.retry_count > 0 && <small>Retry {execution.retry_count}</small>}
                          </div>
                        </li>
                      ))}
                    </ol>
                  </article>
                ))}
                {!executionsByRequest.size && <div className="empty-state">No workflow executions are assigned to this account.</div>}
              </div>
            </section>

            <section className="panel-card details-panel">
              <div className="panel-heading execution-heading">
                <div>
                  <h3>My process execution history</h3>
                  <p>Completed duration excludes unfinished work; active work shows elapsed time.</p>
                </div>
                <label className="execution-search">
                  Search
                  <input value={processSearch} onChange={(event) => setProcessSearch(event.target.value)} placeholder="Request, process, task, status" />
                </label>
                <label className="execution-search">
                  Status
                  <select value={executionStatus} onChange={(event) => setExecutionStatus(event.target.value)}>
                    <option value="">All statuses</option>
                    <option value="Pending">Pending</option>
                    <option value="In Progress">In progress</option>
                    <option value="Completed">Completed</option>
                    <option value="Failed">Failed</option>
                  </select>
                </label>
                <label className="execution-search">
                  Process
                  <input value={processFilter} onChange={(event) => setProcessFilter(event.target.value)} placeholder="Filter process" />
                </label>
                <label className="execution-search">
                  From
                  <input type="date" value={executionDateFrom} onChange={(event) => setExecutionDateFrom(event.target.value)} />
                </label>
                <label className="execution-search">
                  To
                  <input type="date" value={executionDateTo} onChange={(event) => setExecutionDateTo(event.target.value)} />
                </label>
              </div>
              {processExecutionsError && <div className="error-banner" role="alert">{processExecutionsError}</div>}
              {processExecutionsLoading && !processExecutions.length && <div className="loading-panel">Loading filtered process history…</div>}
              <div className="table-scroll">
                <table className="execution-table">
                  <thead>
                    <tr><th>Request</th><th>Process / task</th><th>Status</th><th>Duration</th><th>SLA</th><th>Alert</th></tr>
                  </thead>
                  <tbody>
                    {processExecutions.map((execution) => {
                      const observedMinutes = execution.duration_minutes ?? execution.elapsed_minutes ?? 0;
                      const breached = observedMinutes > execution.sla_target_minutes;
                      return (
                        <tr key={execution.process_execution_id}>
                          <td>{execution.customer_request_id}</td>
                          <td>
                            <details>
                              <summary>{execution.process_name}</summary>
                              <small>{execution.task_name} · {execution.process_execution_id}</small>
                              {execution.retry_count > 0 && <small>Retry count: {execution.retry_count}</small>}
                              {execution.failure_reason && <small>{execution.failure_reason}</small>}
                            </details>
                          </td>
                          <td>{execution.status}</td>
                          <td>{execution.status === 'Pending' ? 'Not started' : execution.duration_minutes === null ? `${execution.elapsed_minutes ?? 0} min elapsed` : `${execution.duration_minutes} min`}</td>
                          <td>{execution.status === 'Pending' ? 'SLA timing not started' : `${breached ? 'Over SLA' : 'Within SLA'} · ${execution.sla_target_minutes} min`}</td>
                          <td>{execution.alert_id ?? 'None'}</td>
                        </tr>
                      );
                    })}
                    {!processExecutions.length && !processExecutionsLoading && <tr><td colSpan={6}>No process executions match these filters.</td></tr>}
                  </tbody>
                </table>
              </div>
              {processExecutions.length < processExecutionTotal && (
                <button className="load-more-records" type="button" onClick={() => void loadMoreProcessExecutions()} disabled={processExecutionsLoading}>
                  {processExecutionsLoading ? 'Loading…' : `Load more (${processExecutions.length} of ${processExecutionTotal})`}
                </button>
              )}
            </section>
            </>}

            {activeView === 'alerts' && <section className="panel-card details-panel">
              <div className="panel-heading"><h3>My alerts</h3></div>
              {alerts.length ? (
                <div className="table-scroll">
                  <table className="execution-table">
                    <thead><tr><th>Alert type</th><th>Severity</th><th>Request / process execution</th><th>Observed</th><th>Threshold</th><th>Status</th><th>Reason</th></tr></thead>
                    <tbody>
                      {alerts.map((alert) => (
                        <tr key={alert.alert_id}>
                          <td>{alert.alert_type}<small>{alert.alert_id}</small></td>
                          <td>{alert.severity}</td>
                          <td>{alert.customer_request_id}<small>{alert.process_execution_id}</small></td>
                          <td>{alert.observed_minutes} min</td>
                          <td>{alert.threshold_minutes} min</td>
                          <td>{alert.resolution_status}</td>
                          <td>{alert.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <div className="empty-state">No alerts for this account.</div>}
            </section>}
          </>
        )}
      </main>
    </div>
  );
}
