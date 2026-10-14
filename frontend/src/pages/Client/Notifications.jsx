import { useEffect, useState } from 'react';
import api from '../../services/api';
import AppShell from '../../components/AppShell';
import './Notifications.css';
import { timeAgo } from '../../utils/time';

// Notifications grouped into categories so the list stays scannable.
// The backend stores one flat array; grouping happens here in memory.

const GROUP_LABELS = {
  bill_uploaded:       { title: 'Invoice Notifications',       sub: 'Updates on uploads and OCR processing.' },
  bill_approved:       { title: 'Invoice Notifications',       sub: 'Updates on uploads and OCR processing.' },
  bill_rejected:       { title: 'Invoice Notifications',       sub: 'Updates on uploads and OCR processing.' },
  reupload_requested:  { title: 'Action Needed',               sub: 'Your CA has asked for a new copy.' },
  client_approved:     { title: 'Account Updates',             sub: 'Changes to your Invexa account.' },
  client_rejected:     { title: 'Account Updates',             sub: 'Changes to your Invexa account.' },
  new_message:         { title: 'Messages',                    sub: 'You have a new chat message.' },
};


export default function Notifications() {
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

  async function markAllRead() {
    await api.put('/notifications/mark-all-read');
    load();
  }

  // Group by the friendly section title.
  const grouped = items.reduce((acc, n) => {
    const cfg = GROUP_LABELS[n.type] || { title: 'Other', sub: '' };
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
          <p className="nt-sub">Stay updated on invoices, GST and CA activity.</p>
        </div>
        <button className="nt-markall" onClick={markAllRead}>Mark all as read</button>
      </div>

      {loading ? (
        <p className="nt-empty">Loading…</p>
      ) : sections.length === 0 ? (
        <div className="nt-empty-card">
          <p>You have no notifications yet.</p>
        </div>
      ) : (
        sections.map(([title, section]) => (
          <section key={title} className="nt-section">
            <h2 className="nt-section__title">{title}</h2>
            <p className="nt-section__sub">{section.sub}</p>

            <ul className="nt-list">
              {section.rows.map((n) => (
                <li key={n.id} className={`nt-item${n.is_read ? '' : ' nt-item--unread'}`}>
                  <span className="nt-item__icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M6 2h9l5 5v15H6z" /><path d="M14 2v5h5" />
                    </svg>
                  </span>
                  <span className="nt-item__text">{n.title} — {n.body}</span>
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