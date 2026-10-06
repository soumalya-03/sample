import React, { useMemo, useState } from 'react';

type Sensitivity = 'High' | 'Medium' | 'Low';

type MailEmail = {
  id: number;
  subject: string;
  from: string;
  mailbox: string;
  source: string;
  sensitivity: Sensitivity;
  date: string;
  attachment: string;
  content: string;
};

type AdvFilters = {
  subject: string;
  sender: string;
  attachment: string;
  sensitivity: '' | Sensitivity;
  from: string;
  to: string;
  hasAttachment: boolean;
};

const EMAILS: MailEmail[] = [
  { id: 1, subject: 'Project Plan Review', from: 'manager@wipro.com', mailbox: 'HP Mailbox', source: 'Exchange', sensitivity: 'High', date: '2026-10-06', attachment: 'ProjectPlan.pdf', content: 'Please review the project plan and provide comments before EOD.' },
  { id: 2, subject: 'Quarter KPI Metrics', from: 'hr@wipro.com', mailbox: 'HR Mailbox', source: 'Outlook', sensitivity: 'Medium', date: '2026-10-05', attachment: 'KPI.xlsx', content: 'KPI metrics for this quarter have been shared.' },
  { id: 3, subject: 'Budget Approval', from: 'finance@wipro.com', mailbox: 'Finance Mailbox', source: 'Teams', sensitivity: 'High', date: '2026-10-04', attachment: 'Budget.pdf', content: 'Kindly review and approve the budget document.' },
  { id: 4, subject: 'Legal Contract Update', from: 'legal@wipro.com', mailbox: 'Legal Mailbox', source: 'Shared Mailbox', sensitivity: 'Low', date: '2026-10-03', attachment: 'Contract.docx', content: 'Updated legal contract attached.' },
];
const MAILBOXES = ['HP Mailbox', 'HR Mailbox', 'Finance Mailbox', 'Legal Mailbox'];
const FEEDS = ['Exchange', 'Outlook', 'Teams', 'Shared Mailbox'];
const EMPTY_ADV: AdvFilters = { subject: '', sender: '', attachment: '', sensitivity: '', from: '', to: '', hasAttachment: false };
const BADGE: Record<Sensitivity, string> = { High: '#ef4444', Medium: '#f59e0b', Low: '#10b981' };
const has = (v: string, q: string) => !q || v.toLowerCase().includes(q.toLowerCase());
const toggle = (list: string[], x: string) => (list.includes(x) ? list.filter((i) => i !== x) : [...list, x]);

const CSS = `
*{box-sizing:border-box}
.edp{min-height:100vh;background:#f1f5f9;font-family:"Segoe UI",system-ui,sans-serif;color:#0f172a}
.edp .hdr{background:#0f172a;color:#fff;display:flex;justify-content:space-between;align-items:center;padding:14px 24px;gap:16px;flex-wrap:wrap}
.edp .hdr h2{margin:0;font-size:20px}
.edp .row{display:flex;gap:8px;align-items:center}
.edp .inp{padding:9px 12px;border:1px solid #cbd5e1;border-radius:8px;font:inherit;width:100%}
.edp .hdr .inp{width:300px;border:none}
.edp .btn{padding:9px 14px;border:none;border-radius:8px;cursor:pointer;font:inherit;font-weight:600;background:#e2e8f0;color:#0f172a;transition:.15s}
.edp .btn:hover{filter:brightness(.92)}.edp .btn:disabled{opacity:.5;cursor:not-allowed}
.edp .pri{background:#2563eb;color:#fff}.edp .dot{background:#f59e0b;border-radius:50%;width:8px;height:8px;display:inline-block;margin-left:6px}
.edp .main{display:grid;grid-template-columns:240px 1fr 380px;gap:16px;padding:16px}
.edp .card{background:#fff;border-radius:12px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.edp .card h3{margin:0 0 12px;font-size:16px}
.edp .chk{display:flex;align-items:center;gap:8px;padding:6px 4px;border-radius:6px;cursor:pointer}
.edp .chk:hover{background:#f1f5f9}.edp .chk span{flex:1}
.edp .x{background:none;border:none;color:#94a3b8;cursor:pointer;font-size:16px}.edp .x:hover{color:#ef4444}
.edp .link{background:none;border:none;color:#2563eb;cursor:pointer;font-size:12px;padding:0}
.edp .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
.edp .stat{color:#fff;padding:14px 16px;border-radius:12px}.edp .stat p{margin:0;opacity:.85;font-size:13px}.edp .stat b{font-size:28px}
.edp table{width:100%;border-collapse:collapse}.edp th{text-align:left;font-size:12px;color:#64748b;text-transform:uppercase;padding:8px}
.edp td{padding:10px 8px;border-top:1px solid #f1f5f9}.edp tbody tr{cursor:pointer}.edp tbody tr:hover{background:#f8fafc}
.edp tr.sel{background:#eff6ff!important}
.edp .badge{color:#fff;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600}
.edp .muted{color:#64748b;font-size:14px}.edp .meta p{margin:6px 0;font-size:14px}
.edp .ov{position:fixed;inset:0;background:rgba(15,23,42,.5);display:flex;justify-content:center;align-items:center}
.edp .modal{width:440px;background:#fff;border-radius:12px;padding:22px;display:grid;gap:10px}
.edp .modal h3{margin:0}.edp .lbl{font-size:12px;color:#64748b}
.edp .err{color:#ef4444;font-size:13px}
`;

type CheckListProps = {
  title: string;
  items: string[];
  sel: string[];
  setSel: (items: string[]) => void;
  onRemove?: (item: string) => void;
};

function CheckList({ title, items, sel, setSel, onRemove }: CheckListProps) {
  return (
    <>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h3>{title}</h3>
        <button className="link" onClick={() => setSel(sel.length === items.length ? [] : items)}>
          {sel.length === items.length ? 'None' : 'All'}
        </button>
      </div>
      {items.map((i) => (
        <label key={i} className="chk">
          <input type="checkbox" checked={sel.includes(i)} onChange={() => setSel(toggle(sel, i))} />
          <span>{i}</span>
          {onRemove && !FEEDS.includes(i) && (
            <button className="x" title="Remove feed" onClick={(e) => { e.preventDefault(); onRemove(i); }}>×</button>
          )}
        </label>
      ))}
    </>
  );
}

export default function EmailDiscoveryPortal() {
  const [searchText, setSearchText] = useState('');
  const [query, setQuery] = useState('');
  const [adv, setAdv] = useState<AdvFilters>(EMPTY_ADV);
  const [draft, setDraft] = useState<AdvFilters>(EMPTY_ADV);
  const [feeds, setFeeds] = useState<string[]>(FEEDS);
  const [selMailboxes, setSelMailboxes] = useState<string[]>(MAILBOXES);
  const [selSources, setSelSources] = useState<string[]>(FEEDS);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [modal, setModal] = useState<'adv' | 'feed' | null>(null);
  const [newFeed, setNewFeed] = useState('');

  const emails = useMemo(
    () =>
      EMAILS.filter(
        (m) =>
          selMailboxes.includes(m.mailbox) &&
          selSources.includes(m.source) &&
          (has(m.subject, query) || has(m.content, query) || has(m.from, query)) &&
          has(m.subject, adv.subject) &&
          has(m.from, adv.sender) &&
          has(m.attachment || '', adv.attachment) &&
          (!adv.sensitivity || m.sensitivity === adv.sensitivity) &&
          (!adv.hasAttachment || !!m.attachment) &&
          (!adv.from || m.date >= adv.from) &&
          (!adv.to || m.date <= adv.to)
      ),
    [selMailboxes, selSources, query, adv]
  );
  const selected = emails.find((m) => m.id === selectedId);
  const advActive = JSON.stringify(adv) !== JSON.stringify(EMPTY_ADV);

  const search = () => {
    setQuery(searchText.trim());
    setSelectedId(null);
  };
  const reset = () => {
    setSearchText(''); setQuery(''); setAdv(EMPTY_ADV); setDraft(EMPTY_ADV);
    setSelMailboxes(MAILBOXES); setSelSources(feeds); setSelectedId(null);
  };
  const feedName = newFeed.trim();
  const feedDup = feeds.some((f) => f.toLowerCase() === feedName.toLowerCase());
  const saveFeed = () => {
    if (!feedName || feedDup) return;
    setFeeds([...feeds, feedName]);
    setSelSources([...selSources, feedName]);
    setNewFeed(''); setModal(null);
  };
  const removeFeed = (f: string) => {
    setFeeds(feeds.filter((x) => x !== f));
    setSelSources(selSources.filter((x) => x !== f));
  };
  const setD = (k: keyof AdvFilters) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const value = e.target.type === 'checkbox' ? (e.target as HTMLInputElement).checked : e.target.value;
    setDraft({ ...draft, [k]: value });
  };

  return (
    <div className="edp">
      <style>{CSS}</style>

      <header className="hdr">
        <h2>Email Discovery Portal</h2>
        <div className="row">
          <input className="inp" placeholder="Search subject, content, sender..." value={searchText}
            onChange={(e) => setSearchText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()} />
          <button className="btn pri" onClick={search}>Search</button>
          <button className="btn" onClick={reset}>Reset</button>
          <button className="btn" onClick={() => { setDraft(adv); setModal('adv'); }}>
            Advanced{advActive && <span className="dot" />}
          </button>
        </div>
      </header>

      <div className="main">
        <aside className="card">
          <CheckList title="📬 Mailboxes" items={MAILBOXES} sel={selMailboxes} setSel={setSelMailboxes} />
          <hr style={{ border: 0, borderTop: '1px solid #e2e8f0', margin: '16px 0' }} />
          <CheckList title="🔗 Sources" items={feeds} sel={selSources} setSel={setSelSources} onRemove={removeFeed} />
          <button className="btn pri" style={{ width: '100%', marginTop: 16 }} onClick={() => setModal('feed')}>+ Add Feed</button>
        </aside>

        <main>
          <div className="stats">
            <div className="stat" style={{ background: '#2563eb' }}><p>Total Emails</p><b>{emails.length}</b></div>
            <div className="stat" style={{ background: '#ef4444' }}><p>High Sensitivity</p><b>{emails.filter((e) => e.sensitivity === 'High').length}</b></div>
            <div className="stat" style={{ background: '#10b981' }}><p>Active Sources</p><b>{selSources.length}</b></div>
          </div>
          <div className="card">
            <h3>📋 Search Results</h3>
            {emails.length ? (
              <table>
                <thead><tr><th>Subject</th><th>Mailbox</th><th>Date</th><th>Sensitivity</th></tr></thead>
                <tbody>
                  {emails.map((m) => (
                    <tr key={m.id} className={m.id === selectedId ? 'sel' : ''} onClick={() => setSelectedId(m.id)}>
                      <td>{m.subject}</td><td>{m.mailbox}</td><td>{m.date}</td>
                      <td><span className="badge" style={{ background: BADGE[m.sensitivity] }}>{m.sensitivity}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted">No emails match your filters. <button className="link" onClick={reset}>Clear all filters</button></p>
            )}
          </div>
        </main>

        <section className="card">
          <h3>📩 Email Preview</h3>
          {selected ? (
            <div className="meta">
              <h2 style={{ margin: '0 0 10px' }}>{selected.subject}</h2>
              <p><b>From:</b> {selected.from}</p>
              <p><b>Mailbox:</b> {selected.mailbox}</p>
              <p><b>Source:</b> {selected.source}</p>
              <p><b>Date:</b> {selected.date}</p>
              <p><b>Sensitivity:</b> <span className="badge" style={{ background: BADGE[selected.sensitivity] }}>{selected.sensitivity}</span></p>
              <hr /><p>{selected.content}</p><hr />
              {selected.attachment && <p>📎 {selected.attachment}</p>}
            </div>
          ) : (
            <p className="muted">Select an email from search results.</p>
          )}
        </section>
      </div>

      {modal === 'adv' && (
        <div className="ov" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Advanced Search</h3>
            <input className="inp" placeholder="Subject" value={draft.subject} onChange={setD('subject')} />
            <input className="inp" placeholder="Sender email" value={draft.sender} onChange={setD('sender')} />
            <input className="inp" placeholder="Attachment name" value={draft.attachment} onChange={setD('attachment')} />
            <select className="inp" value={draft.sensitivity} onChange={setD('sensitivity')}>
              <option value="">All sensitivities</option><option>High</option><option>Medium</option><option>Low</option>
            </select>
            <div className="row">
              <div style={{ flex: 1 }}><span className="lbl">From</span><input className="inp" type="date" value={draft.from} max={draft.to || undefined} onChange={setD('from')} /></div>
              <div style={{ flex: 1 }}><span className="lbl">To</span><input className="inp" type="date" value={draft.to} min={draft.from || undefined} onChange={setD('to')} /></div>
            </div>
            <label className="chk"><input type="checkbox" checked={draft.hasAttachment} onChange={setD('hasAttachment')} /> Has attachment</label>
            <div className="row" style={{ justifyContent: 'space-between', marginTop: 8 }}>
              <button className="btn" onClick={() => setDraft(EMPTY_ADV)}>Clear</button>
              <div className="row">
                <button className="btn" onClick={() => setModal(null)}>Cancel</button>
                <button className="btn pri" onClick={() => { setAdv(draft); setSelectedId(null); setModal(null); }}>Apply Filters</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {modal === 'feed' && (
        <div className="ov" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Add Feed</h3>
            <input className="inp" autoFocus placeholder="Feed name" value={newFeed}
              onChange={(e) => setNewFeed(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && saveFeed()} />
            {feedDup && feedName && <span className="err">Feed already exists.</span>}
            <div className="row" style={{ justifyContent: 'flex-end' }}>
              <button className="btn" onClick={() => { setNewFeed(''); setModal(null); }}>Cancel</button>
              <button className="btn pri" disabled={!feedName || feedDup} onClick={saveFeed}>Save Feed</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
