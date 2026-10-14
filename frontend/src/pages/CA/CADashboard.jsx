import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import AppShell from '../../components/AppShell';
import { useAuth } from '../../context/AuthContext';
import { formatDateTime } from '../../utils/time';
import './CADashboard.css';

// CA dashboard: only activity. The invite code lives in the CA
// profile page so it is not accidentally shown on a shared screen.
export default function CADashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [pending, setPending] = useState([]);
  const [recent, setRecent] = useState([]);
  const [stats, setStats] = useState({ pending: 0, approved: 0, rejected: 0, total: 0 });
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [p, r, s] = await Promise.all([
        api.get('/firm/list-join-requests'),
        api.get('/invoice/list-firm-invoices?page_size=6'),
        api.get('/review/stats').catch(() => ({ data: { pending: 0, approved: 0, rejected: 0, total: 0 } })),
      ]);
      setPending(p.data.clients || []);
      setRecent(r.data.invoices || []);
      setStats(s.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function decide(clientId, approve) {
    try {
      if (approve) await api.post(`/firm/approve-client/${clientId}`);
      else await api.post(`/firm/reject-client/${clientId}`);
      setPending((prev) => prev.filter((c) => c.id !== clientId));
      load();
    } catch (err) {
      alert(err.response?.data?.message || 'Action failed');
    }
  }

  if (loading) {
    return <AppShell><p style={{ padding: 40, color: '#64748B' }}>Loading…</p></AppShell>;
  }

  const TILES = [
    { key: 'pending', label: 'Awaiting review', filter: 'uploaded' },
    { key: 'approved', label: 'Approved', filter: 'approved' },
    { key: 'rejected', label: 'Rejected', filter: 'rejected' },
    { key: 'total', label: 'Total bills', filter: '' },
  ];

  return (
    <AppShell>
      <h1 className="ca-greeting">Welcome, {user?.name || 'CA'}</h1>
      <p className="ca-sub">{user?.firm_name}</p>

      <section className="ca-stats-4">
        {TILES.map((t) => (
          <button
            key={t.key}
            className="ca-stat"
            onClick={() => navigate(t.filter ? `/ca/documents?status=${t.filter}` : '/ca/documents')}
          >
            <span className="ca-stat__num">{stats[t.key] ?? 0}</span>
            <span className="ca-stat__lbl">{t.label}</span>
          </button>
        ))}
      </section>

      <div className="ca-grid">
        <section className="ca-card">
          <div className="ca-card__head">
            <h2 className="ca-card__title">Client requests</h2>
            <Link to="/ca/clients" className="ca-link">View all →</Link>
          </div>

          {pending.length === 0 ? (
            <p className="ca-muted">No pending requests.</p>
          ) : (
            <ul className="ca-requests">
              {pending.map((c) => (
                <li key={c.id} className="ca-request">
                  <div>
                    <p className="ca-request__name">{c.business_name}</p>
                    <p className="ca-request__sub">{c.owner_name} · {c.email}</p>
                  </div>
                  <div className="ca-request__actions">
                    <button className="ca-btn ca-btn--danger" onClick={() => decide(c.id, false)}>Reject</button>
                    <button className="ca-btn ca-btn--primary" onClick={() => decide(c.id, true)}>Approve</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="ca-card">
          <div className="ca-card__head">
            <h2 className="ca-card__title">Recent bills</h2>
            <Link to="/ca/documents" className="ca-link">All bills →</Link>
          </div>

          {recent.length === 0 ? (
            <p className="ca-muted">No bills yet.</p>
          ) : (
            <ul className="ca-recent">
              {recent.map((b) => (
                <li key={b.id} className="ca-recent__item" onClick={() => navigate('/ca/documents')}>
                  <div>
                    <p className="ca-recent__file">{b.file_name}</p>
                    <p className="ca-recent__sub">
                      {b.client_name || 'Client'} · {formatDateTime(b.uploaded_at)}
                    </p>
                  </div>
                  <span className={`ca-pill ca-pill--${b.status}`}>
                    {b.status.replace('_', ' ')}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </AppShell>
  );
}