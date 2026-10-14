import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../../services/api';
import AppShell from '../../components/AppShell';
import BillReviewModal from '../../components/BillReviewModal';
import { formatDateTime, timeAgo } from '../../utils/time';
import './CADocuments.css';

// CA bill queue. A left sidebar lists every client in the firm so
// the CA can pick one and see only that client's bills. When "All"
// is selected, bills are grouped under client section headers so
// nothing gets mixed up.
//
// The table row click opens the review modal; the client name is
// always visible in the modal header so approval is unambiguous.

const TABS = [
  { key: '',                    label: 'All' },
  { key: 'uploaded',            label: 'New' },
  { key: 'pending_review',      label: 'In Review' },
  { key: 'approved',            label: 'Approved' },
  { key: 'rejected',            label: 'Rejected' },
  { key: 'reupload_requested',  label: 'Reupload' },
];

const STATUS_LABEL = {
  uploaded: 'New',
  pending_review: 'In Review',
  approved: 'Approved',
  rejected: 'Rejected',
  reupload_requested: 'Reupload',
};

export default function CADocuments() {
  const [params, setParams] = useSearchParams();
  const tab = params.get('status') || '';
  const query = params.get('q') || '';
  const clientFilter = params.get('client') || '';

  const [bills, setBills] = useState([]);
  const [clients, setClients] = useState([]);
  const [counts, setCounts] = useState({});
  const [loading, setLoading] = useState(true);
  const [openBillId, setOpenBillId] = useState(null);
  const [draftQ, setDraftQ] = useState(query);

  useEffect(() => { setDraftQ(query); }, [query]);

  // Load the sidebar client list once.
  useEffect(() => {
    api.get('/firm/list-clients?status=active')
      .then((res) => setClients(res.data.clients || []))
      .catch(() => setClients([]));
  }, []);

  async function load() {
    setLoading(true);
    try {
      const p = new URLSearchParams();
      if (tab) p.append('status', tab);
      if (query) p.append('q', query);
      if (clientFilter) p.append('client_id', clientFilter);
      const res = await api.get(`/invoice/list-firm-invoices?${p.toString()}`);
      setBills(res.data.invoices || []);
    } catch {
      setBills([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [tab, query, clientFilter]);

  // Recount tab badges on every list change.
  useEffect(() => {
    api.get('/invoice/list-firm-invoices?page_size=200')
      .then((res) => {
        const next = {};
        for (const inv of res.data.invoices || []) {
          next[inv.status] = (next[inv.status] || 0) + 1;
        }
        setCounts(next);
      })
      .catch(() => {});
  }, [bills.length, openBillId]);

  function setParam(key, value) {
    const p = new URLSearchParams(params);
    if (value) p.set(key, value);
    else p.delete(key);
    setParams(p, { replace: true });
  }

  function applySearch(e) {
    e.preventDefault();
    setParam('q', draftQ.trim());
  }

  function clearSearch() {
    setDraftQ('');
    setParam('q', '');
  }

  // Group bills by client when viewing All; keep flat when a
  // specific client is selected.
  const grouped = useMemo(() => {
    if (clientFilter) return [{ clientName: '', bills }];
    const map = {};
    for (const b of bills) {
      const key = b.client_name || 'Unknown client';
      if (!map[key]) map[key] = [];
      map[key].push(b);
    }
    return Object.entries(map).map(([clientName, rows]) => ({ clientName, bills: rows }));
  }, [bills, clientFilter]);

  const totalCount = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <AppShell>
      <div className="doc-layout">
        {/* Sidebar */}
        <aside className="doc-sidebar">
          <h3 className="doc-sidebar__title">Clients</h3>
          <button
            className={`doc-client${!clientFilter ? ' doc-client--active' : ''}`}
            onClick={() => setParam('client', '')}
          >
            <span>All clients</span>
            <span className="doc-client__count">{totalCount}</span>
          </button>

          {clients.map((c) => (
            <button
              key={c.id}
              className={`doc-client${clientFilter === c.id ? ' doc-client--active' : ''}`}
              onClick={() => setParam('client', c.id)}
            >
              <span className="doc-client__name">{c.business_name}</span>
              <span className="doc-client__owner">{c.owner_name}</span>
            </button>
          ))}
        </aside>

        {/* Main */}
        <div className="doc-main">
          <div className="doc-head">
            <div>
              <h1 className="doc-title">
                {clientFilter
                  ? (clients.find((c) => c.id === clientFilter)?.business_name || 'Documents')
                  : 'Documents'}
              </h1>
              <p className="doc-sub">
                {bills.length} bill{bills.length === 1 ? '' : 's'} shown
                {query && ` · matching "${query}"`}
              </p>
            </div>

            <form className="doc-search" onSubmit={applySearch}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" />
              </svg>
              <input
                type="text"
                value={draftQ}
                onChange={(e) => setDraftQ(e.target.value)}
                placeholder="Search file, vendor, invoice #"
              />
              {query && <button type="button" className="doc-search__clear" onClick={clearSearch}>×</button>}
            </form>
          </div>

          <div className="doc-tabs">
            {TABS.map((t) => {
              const count = t.key ? (counts[t.key] || 0) : totalCount;
              return (
                <button
                  key={t.key}
                  className={`doc-tab${tab === t.key ? ' doc-tab--active' : ''}`}
                  onClick={() => setParam('status', t.key)}
                >
                  {t.label}
                  <span className="doc-tab__count">{count}</span>
                </button>
              );
            })}
          </div>

          {loading ? (
            <p className="doc-muted">Loading bills…</p>
          ) : bills.length === 0 ? (
            <div className="doc-empty">
              <p className="doc-empty__title">
                {query ? 'No bills match that search' : 'No bills here yet'}
              </p>
              <p className="doc-empty__sub">
                {query ? 'Try a different word.' : 'Client uploads appear here.'}
              </p>
            </div>
          ) : (
            grouped.map((section, idx) => (
              <section key={idx} className="doc-group">
                {section.clientName && (
                  <h3 className="doc-group__title">
                    {section.clientName}
                    <span className="doc-group__count">{section.bills.length}</span>
                  </h3>
                )}
                <div className="doc-table-wrap">
                  <table className="doc-table">
                    <thead>
                      <tr>
                        {!clientFilter && <th>Client</th>}
                        <th>File</th>
                        <th>Vendor</th>
                        <th>Amount</th>
                        <th>Uploaded at</th>
                        <th>Status</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {section.bills.map((b) => (
                        <tr key={b.id} className="doc-row" onClick={() => setOpenBillId(b.id)}>
                          {!clientFilter && <td><strong>{b.client_name || '—'}</strong></td>}
                          <td className="doc-muted">{b.file_name}</td>
                          <td>{b.vendor_name || <span className="doc-muted">—</span>}</td>
                          <td>
                            {b.total_amount
                              ? `₹${Number(b.total_amount).toLocaleString('en-IN')}`
                              : <span className="doc-muted">—</span>}
                          </td>
                          <td className="doc-muted">
                            {formatDateTime(b.uploaded_at)}
                            <span className="doc-ago"> · {timeAgo(b.uploaded_at)}</span>
                          </td>
                          <td>
                            <span className={`ca-pill ca-pill--${b.status}`}>
                              {STATUS_LABEL[b.status] || b.status}
                            </span>
                          </td>
                          <td><button className="doc-open">Open →</button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ))
          )}
        </div>
      </div>

      {openBillId && (
        <BillReviewModal
          billId={openBillId}
          onClose={() => { setOpenBillId(null); load(); }}
        />
      )}
    </AppShell>
  );
}