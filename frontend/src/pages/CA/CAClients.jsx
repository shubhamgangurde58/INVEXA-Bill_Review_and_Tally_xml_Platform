import { useEffect, useState } from 'react';
import api from '../../services/api';
import AppShell from '../../components/AppShell';
import { useAuth } from '../../context/AuthContext';
import { formatDateTime } from '../../utils/time';
import './CAClients.css';

const TABS = [
  { key: 'active',   label: 'Active' },
  { key: 'pending',  label: 'Pending' },
  { key: 'rejected', label: 'Rejected' },
];

export default function CAClients() {
  const { user } = useAuth();
  const [tab, setTab] = useState('active');
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  async function load() {
    setLoading(true);
    try {
      const path = tab === 'pending'
        ? '/firm/list-join-requests'
        : `/firm/list-clients?status=${tab}`;
      const res = await api.get(path);
      setClients(res.data.clients || []);
    } catch {
      setClients([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [tab]);

  async function decide(id, approve) {
    setBusy(id);
    try {
      if (approve) await api.post(`/firm/approve-client/${id}`);
      else await api.post(`/firm/reject-client/${id}`);
      load();
    } catch (err) {
      alert(err.response?.data?.message || 'Action failed');
    } finally {
      setBusy('');
    }
  }

  return (
    <AppShell>
      <section className="ca-card">
        <div className="ca-tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={`ca-tab${tab === t.key ? ' ca-tab--active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {loading ? (
          <p className="ca-muted">Loading…</p>
        ) : clients.length === 0 ? (
          <p className="ca-muted">No {tab} clients.</p>
        ) : (
          <table className="ca-table">
            <thead>
              <tr>
                <th>Business</th>
                <th>Owner</th>
                <th>Email</th>
                <th>Mobile</th>
                <th>GSTIN</th>
                <th>Status</th>
                {tab === 'pending' && <th />}
              </tr>
            </thead>
            <tbody>
              {clients.map((c) => (
                <tr key={c.id}>
                  <td><strong>{c.business_name}</strong></td>
                  <td>{c.owner_name}</td>
                  <td>{c.email}</td>
                  <td>{c.mobile || '—'}</td>
                  <td>{c.gstin || '—'}</td>
                  <td><span className={`ca-pill ca-pill--${c.status}`}>{c.status}</span></td>
                  {tab === 'pending' && (
                    <td>
                      <div className="ca-row-actions">
                        <button
                          className="ca-btn ca-btn--danger"
                          onClick={() => decide(c.id, false)}
                          disabled={busy === c.id}
                        >
                          Reject
                        </button>
                        <button
                          className="ca-btn ca-btn--primary"
                          onClick={() => decide(c.id, true)}
                          disabled={busy === c.id}
                        >
                          Approve
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </AppShell>
  );
}