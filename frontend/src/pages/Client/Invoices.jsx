import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../../services/api';
import AppShell from '../../components/AppShell';
import { formatDateTime, timeAgo } from '../../utils/time';
import './Invoices.css';

// Full list of the client's bills with search, status filter, and
// per-bill actions. Search term and status live in the URL so the
// browser back button works and the top-bar search can jump here.

const FILTERS = [
  { key: 'all',                label: 'All' },
  { key: 'uploaded',           label: 'With CA' },
  { key: 'pending_review',     label: 'In Review' },
  { key: 'approved',           label: 'Approved' },
  { key: 'rejected',           label: 'Rejected' },
  { key: 'reupload_requested', label: 'Action Needed' },
];

const STATUS_LABEL = {
  uploaded: 'With CA',
  pending_review: 'In Review',
  approved: 'Approved',
  rejected: 'Rejected',
  reupload_requested: 'Action Needed',
};

export default function Invoices() {
  const [params, setParams] = useSearchParams();
  const filter = params.get('status') || 'all';
  const query = params.get('q') || '';

  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [reuploadId, setReuploadId] = useState(null);
  const [reuploadFile, setReuploadFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [reuploadError, setReuploadError] = useState('');

  const [draftQ, setDraftQ] = useState(query);
  useEffect(() => { setDraftQ(query); }, [query]);

  async function load() {
    setLoading(true); setError('');
    try {
      const p = new URLSearchParams();
      if (filter !== 'all') p.append('status', filter);
      if (query) p.append('q', query);
      const res = await api.get(`/client/list-my-invoices?${p.toString()}`);
      setRows(res.data.invoices || []);
      setTotal(res.data.total ?? (res.data.invoices || []).length);
    } catch (err) {
      setError(err.response?.data?.message || 'Could not load invoices.');
      setRows([]); setTotal(0);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [filter, query]);

  function setFilter(next) {
    const p = new URLSearchParams(params);
    if (next === 'all') p.delete('status');
    else p.set('status', next);
    setParams(p, { replace: true });
  }

  function applySearch(e) {
    e.preventDefault();
    const p = new URLSearchParams(params);
    if (draftQ.trim()) p.set('q', draftQ.trim());
    else p.delete('q');
    setParams(p, { replace: true });
  }

  function clearSearch() {
    setDraftQ('');
    const p = new URLSearchParams(params);
    p.delete('q');
    setParams(p, { replace: true });
  }

  function downloadXml(invoiceId, invoiceNumber) {
    const token = localStorage.getItem('invexa_token');
    const url = `http://127.0.0.1:5000/api/xml/download/${invoiceId}?token=${token}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = `INVEXA_${invoiceNumber || invoiceId}.xml`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  async function deleteInvoice(invoiceId, fileName) {
    const yes = window.confirm(`Delete "${fileName}"? This cannot be undone.`);
    if (!yes) return;
    try {
      await api.delete(`/client/delete-invoice/${invoiceId}`);
      load();
    } catch (err) {
      alert(err.response?.data?.message || 'Delete failed.');
    }
  }

  async function submitReupload(e) {
    e.preventDefault();
    if (!reuploadFile) return;
    setBusy(true); setReuploadError('');
    const body = new FormData();
    body.append('file', reuploadFile);
    try {
      await api.put(`/client/reupload-invoice/${reuploadId}`, body, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setReuploadId(null);
      setReuploadFile(null);
      load();
    } catch (err) {
      setReuploadError(err.response?.data?.message || 'Reupload failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="inv-head">
        <div>
          <h1 className="inv-title">My Invoices</h1>
          <p className="inv-sub">
            {total} {total === 1 ? 'bill' : 'bills'}
            {query && ` · matching "${query}"`}
          </p>
        </div>

        <form className="inv-search" onSubmit={applySearch}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3.5-3.5" />
          </svg>
          <input
            type="text"
            value={draftQ}
            onChange={(e) => setDraftQ(e.target.value)}
            placeholder="Search by file, vendor or invoice #"
          />
          {query && (
            <button type="button" className="inv-search__clear" onClick={clearSearch}>
              ×
            </button>
          )}
        </form>
      </div>

      <div className="inv-filters">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            className={`inv-filter${filter === f.key ? ' inv-filter--active' : ''}`}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <section className="inv-card">
        {loading ? (
          <p className="inv-empty">Loading…</p>
        ) : error ? (
          <p className="inv-empty" style={{ color: '#B91C1C' }}>{error}</p>
        ) : rows.length === 0 ? (
          <div className="inv-empty-state">
            <p className="inv-empty-state__title">
              {query ? 'No invoices match your search' : 'No invoices here yet'}
            </p>
            <p className="inv-empty-state__sub">
              {query
                ? 'Try a different word, or clear the search.'
                : 'Upload a bill from your dashboard and it will show up here.'}
            </p>
          </div>
        ) : (
          <table className="inv-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Invoice #</th>
                <th>Vendor</th>
                <th>Amount</th>
                <th>Uploaded at</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td><strong>{r.file_name}</strong></td>
                  <td>{r.invoice_number || <span className="inv-muted">—</span>}</td>
                  <td>{r.vendor_name || <span className="inv-muted">—</span>}</td>
                  <td>
                    {r.total_amount
                      ? `₹${Number(r.total_amount).toLocaleString('en-IN')}`
                      : <span className="inv-muted">—</span>}
                  </td>
                  <td className="inv-muted">
                    {formatDateTime(r.uploaded_at)}
                    <span className="inv-ago"> · {timeAgo(r.uploaded_at)}</span>
                  </td>
                  <td>
                    <span className={`inv-pill inv-pill--${r.status}`}>
                      {STATUS_LABEL[r.status] || r.status}
                    </span>
                  </td>
                  <td className="inv-actions">
                    {r.status === 'uploaded' && (
                      <button
                        className="inv-btn inv-btn--danger"
                        onClick={() => deleteInvoice(r.id, r.file_name)}
                      >
                        Delete
                      </button>
                    )}
                    {r.status === 'approved' && (
                      <button
                        className="inv-btn inv-btn--primary"
                        onClick={() => downloadXml(r.id, r.invoice_number)}
                      >
                        Download XML
                      </button>
                    )}
                    {r.status === 'reupload_requested' && (
                      <button
                        className="inv-btn inv-btn--warn"
                        onClick={() => setReuploadId(r.id)}
                      >
                        Upload new photo
                      </button>
                    )}
                    {r.status === 'rejected' && r.remarks && (
                      <span className="inv-reason" title={r.remarks}>Reason</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {reuploadId && (
        <div className="inv-modal-overlay" onClick={() => setReuploadId(null)}>
          <form className="inv-modal" onClick={(e) => e.stopPropagation()} onSubmit={submitReupload}>
            <h2>Upload a clearer photo</h2>
            <p>Your CA asked for a new copy of this bill.</p>
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={(e) => setReuploadFile(e.target.files[0] || null)}
            />
            {reuploadError && <div className="inv-error">{reuploadError}</div>}
            <div className="inv-modal__actions">
              <button
                type="button"
                className="inv-btn inv-btn--ghost"
                onClick={() => setReuploadId(null)}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="inv-btn inv-btn--primary"
                disabled={busy || !reuploadFile}
              >
                {busy ? 'Uploading…' : 'Upload'}
              </button>
            </div>
          </form>
        </div>
      )}
    </AppShell>
  );
}