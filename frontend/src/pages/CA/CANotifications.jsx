import { useEffect, useState } from 'react';
import api from '../../services/api';
import AppShell from '../../components/AppShell';
import { timeAgo } from '../../utils/time';
import './CANotifications.css';

const GROUP_TITLE = {
  bill_uploaded:      { title: 'New bills',       sub: 'Clients uploaded bills for you to review.' },
  client_joined:      { title: 'New clients',     sub: 'Requests to join your firm.' },
  new_message:        { title: 'Messages',        sub: 'New chat messages.' },
  bill_approved:      { title: 'Activity',        sub: 'Bills you approved.' },
  bill_rejected:      { title: 'Activity',        sub: 'Bills you rejected.' },
  reupload_requested: { title: 'Activity',        sub: 'Bills you asked to be reuploaded.' },
  client_approved:    { title: 'Activity',        sub: 'Clients you approved.' },
  client_rejected:    { title: 'Activity',        sub: 'Clients you rejected.' },
};

export default function CANotifications() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const res = await api.get('/notifications/list');
      setItems(res.data.notifications || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function markAll() {
    await api.put('/notifications/mark-all-read');
    load();
  }

  const grouped = items.reduce((acc, n) => {
    const cfg = GROUP_TITLE[n.type] || { title: 'Other', sub: '' };
    if (!acc[cfg.title]) acc[cfg.title] = { sub: cfg.sub, rows: [] };
    acc[cfg.title].rows.push(n);
    return acc;
  }, {});
  const sections = Object.entries(grouped);

  return (
    <AppShell>
      <div className="nt-head">
        <div>
          <h1 className="nt-title">Notifications</h1>
          <p className="nt-sub">Client activity, bills and messages.</p>
        </div>
        <button className="nt-markall" onClick={markAll}>Mark all as read</button>
      </div>

      {loading ? (
        <p className="nt-empty">Loading…</p>
      ) : sections.length === 0 ? (
        <div className="nt-empty-card"><p>No notifications yet.</p></div>
      ) : (
        sections.map(([title, section]) => (
          <section key={title} className="nt-section">
            <h2 className="nt-section__title">{title}</h2>
            <p className="nt-section__sub">{section.sub}</p>
            <ul className="nt-list">
              {section.rows.map((n) => (
                <li key={n.id} className={`nt-item${n.is_read ? '' : ' nt-item--unread'}`}>
                  <span className="nt-item__text">
                    <strong>{n.title}</strong> — {n.body}
                  </span>
                  <span className="nt-item__time">{timeAgo(n.created_at)}</span>
                  {!n.is_read && <span className="nt-item__dot" />}
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </AppShell>
  );
}