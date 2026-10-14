import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import AppShell from '../../components/AppShell';
import { useAuth } from '../../context/AuthContext';
import { formatDateTime, timeAgo, formatFull } from '../../utils/time';
import './Dashboard.css';

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

const QUICK_ACTIONS = [
  { icon: 'upload', label: 'Upload Invoice', desc: 'Add a new bill',     action: 'upload' },
  { icon: 'search', label: 'Track Invoice',  desc: 'See live status',    action: '/client/invoices' },
  { icon: 'clock',  label: 'Invoice History', desc: 'Browse past bills', action: '/client/invoices' },
  { icon: 'file',   label: 'Notifications',  desc: 'What changed',      action: '/client/notifications' },
];

function QIcon({ name, size = 20 }) {
  const paths = {
    upload: <><path d="M12 15V4M12 4L8 8M12 4l4 4" /><path d="M4 15v3a2 2 0 002 2h12a2 2 0 002-2v-3" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></>,
    clock:  <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    file:   <><path d="M7 3h7l5 5v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1z" /><path d="M14 3v5h5" /></>,
    cloud:  <><path d="M7 18a4.5 4.5 0 01-.4-9 5.5 5.5 0 0110.7-1.8A4.5 4.5 0 0117 18H7z" /><path d="M12 12v6M9.5 14.5L12 12l2.5 2.5" /></>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
         stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  );
}

// Only three summary tiles. Clicking one jumps to the invoices page
// with the matching status filter in the URL.
const TILES = [
  { key: 'total',    label: 'Total Uploaded', filter: 'all' },
  { key: 'approved', label: 'Approved',       filter: 'approved' },
  { key: 'rejected', label: 'Rejected',       filter: 'rejected' },
];

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [stats, setStats] = useState({ total: 0, approved: 0, rejected: 0 });
  const [recent, setRecent] = useState([]);
  const [search, setSearch] = useState('');

  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [s, l] = await Promise.all([
          api.get('/client/dashboard-stats'),
          api.get('/client/list-my-invoices?page_size=10'),
        ]);
        if (cancelled) return;
        setStats({
          total: s.data.total || 0,
          approved: s.data.approved || 0,
          rejected: s.data.rejected || 0,
        });
        setRecent(l.data.invoices || []);
      } catch (err) {
        console.error('Dashboard load failed:', err);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [refreshKey]);

  async function upload(e) {
    e.preventDefault();
    if (!file) { setError('Please choose a file.'); return; }
    setBusy(true); setError(''); setMessage('');
    const body = new FormData();
    body.append('file', file);
    try {
      await api.post('/client/upload-invoice', body, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setMessage('Uploaded. Your CA will review it shortly.');
      setFile(null);
      const el = document.getElementById('dash-file');
      if (el) el.value = '';
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setError(err.response?.data?.message || 'Upload failed.');
    } finally {
      setBusy(false);
    }
  }

  function scrollToUpload() {
    document.getElementById('upload-card')?.scrollIntoView({ behavior: 'smooth' });
  }

  const visible = recent.filter((b) => {
    if (!search.trim()) return true;
    const t = search.toLowerCase();
    return (
      (b.file_name || '').toLowerCase().includes(t) ||
      (b.invoice_number || '').toLowerCase().includes(t) ||
      (b.vendor_name || '').toLowerCase().includes(t)
    );
  });

  if (user?.status === 'pending') {
    return (
      <AppShell>
        <div className="cl-waiting">
          <h1>Waiting for approval</h1>
          <p>
            <strong>{user?.firm_name}</strong> has received your signup.
            You can upload bills once they approve your account.
          </p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      {/* Welcome banner */}
      <section className="cl-welcome">
        <div className="cl-welcome__copy">
          <span className="cl-welcome__eyebrow">{greeting()}</span>
          <h1 className="cl-welcome__title">
            Welcome back, {user?.business_name || user?.name || 'friend'}
          </h1>
          <p className="cl-welcome__desc">
            You have {stats.total} bills on record, {stats.approved} approved.
          </p>
          <div className="cl-welcome__actions">
            <button className="cl-btn cl-btn--primary" onClick={scrollToUpload}>
              <QIcon name="upload" size={16} /> Upload Invoice
            </button>
            <button className="cl-btn cl-btn--ghost" onClick={() => navigate('/client/invoices')}>
              View all invoices →
            </button>
          </div>
        </div>
      </section>

      {/* Three summary tiles */}
      <section className="cl-stats-3">
        {TILES.map((t) => (
          <button
            key={t.key}
            className="cl-stat-tile"
            onClick={() => navigate(`/client/invoices?status=${t.filter}`)}
          >
            <span className="cl-stat-tile__num">{stats[t.key] ?? 0}</span>
            <span className="cl-stat-tile__lbl">{t.label}</span>
          </button>
        ))}
      </section>

      {/* Quick actions */}
      <section className="cl-quick">
        {QUICK_ACTIONS.map((a) => (
          <button
            key={a.label}
            className="cl-quick-card"
            onClick={() => a.action === 'upload' ? scrollToUpload() : navigate(a.action)}
          >
            <span className="cl-quick-icon"><QIcon name={a.icon} /></span>
            <span className="cl-quick-label">{a.label}</span>
            <span className="cl-quick-desc">{a.desc}</span>
          </button>
        ))}
      </section>

      {/* Upload zone */}
      <section className="cl-upload-card" id="upload-card">
        <h2 className="cl-upload-card__title">Upload Invoice</h2>
        <form onSubmit={upload}>
          <input
            id="dash-file"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={(e) => setFile(e.target.files[0] || null)}
            style={{ display: 'none' }}
          />
          <label htmlFor="dash-file" className="cl-dropzone">
            <span className="cl-dropzone__icon"><QIcon name="cloud" size={26} /></span>
            <span className="cl-dropzone__title">
              {file ? file.name : 'Drag & drop your invoice here'}
            </span>
            <span className="cl-dropzone__sub">
              Supported formats: PDF, PNG, JPG · Max 10MB
            </span>
            <span className="cl-btn cl-btn--primary cl-dropzone__browse">Browse Files</span>
          </label>

          {file && (
            <div className="cl-upload-actions">
              <button type="submit" className="cl-btn cl-btn--primary" disabled={busy}>
                {busy ? 'Uploading…' : 'Upload now'}
              </button>
              <button
                type="button"
                className="cl-btn cl-btn--ghost"
                onClick={() => {
                  setFile(null);
                  document.getElementById('dash-file').value = '';
                }}
              >
                Cancel
              </button>
            </div>
          )}

          {error && <div className="cl-error">{error}</div>}
          {message && <div className="cl-ok">{message}</div>}
        </form>
      </section>

      {/* Recent bills with inline search */}
      <section className="cl-card">
        <div className="cl-card__head">
          <h2 className="cl-card__title">Recent bills</h2>
          <div className="cl-inline-search">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter bills…"
            />
          </div>
        </div>

        {visible.length === 0 ? (
          <p className="cl-muted">
            {recent.length === 0
              ? 'No bills yet. Upload your first one above.'
              : 'No bills match that search.'}
          </p>
        ) : (
          <table className="cl-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Status</th>
                <th>Uploaded at</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((inv) => (
                <tr key={inv.id}>
                  <td><strong>{inv.file_name}</strong></td>
                  <td>
                    <span className={`cl-pill cl-pill--${inv.status}`}>
                      {inv.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td
                    className="cl-muted"
                    title={formatFull(inv.uploaded_at)}
                  >
                    {formatDateTime(inv.uploaded_at)}
                    <span className="cl-ago"> · {timeAgo(inv.uploaded_at)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </AppShell>
  );
}