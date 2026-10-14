import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { timeAgo } from '../utils/time';
import './NotificationsBell.css';

// Small bell in the top bar. Polls the unread count every 15
// seconds so the red dot stays fresh without a WebSocket. Clicking
// the bell opens a dropdown with the last 20 notifications; each
// item links to the relevant page and marks itself as read.
export default function NotificationsBell() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [count, setCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [loadingList, setLoadingList] = useState(false);
  const wrapRef = useRef(null);

  // Poll every 15 seconds. cancel flag stops the loop if the
  // component unmounts mid-request.
  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const res = await api.get('/notifications/unread-count');
        if (!cancelled) setCount(res.data.count || 0);
      } catch { /* silent */ }
    }
    poll();
    const id = setInterval(poll, 15000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  // Close on click outside.
  useEffect(() => {
    function onClick(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  async function loadList() {
    setLoadingList(true);
    try {
      const res = await api.get('/notifications/list');
      setItems(res.data.notifications || []);
    } catch {
      setItems([]);
    } finally {
      setLoadingList(false);
    }
  }

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next) await loadList();
  }

  // Mark this one as read, close the dropdown, then go where the
  // notification points. If it has no link, just refresh the list.
  async function openItem(n) {
    try {
      await api.put(`/notifications/mark-read/${n.id}`);
    } catch { /* silent */ }

    setCount((c) => Math.max(0, c - (n.is_read ? 0 : 1)));
    setOpen(false);

    if (n.link_to) {
      navigate(n.link_to);
    } else {
      await loadList();
    }
  }

  // Fallback list page for the "View all" footer link.
  const allLink = user?.role === 'ca' ? '/ca/notifications' : '/client/notifications';

  return (
    <div className="nb" ref={wrapRef}>
      <button className="nb__btn" onClick={toggle} title="Notifications" aria-label="Notifications">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 9a6 6 0 1112 0c0 4 1.5 5.5 1.5 5.5H4.5S6 13 6 9z" />
          <path d="M10 19a2 2 0 004 0" />
        </svg>
        {count > 0 && <span className="nb__dot">{count > 9 ? '9+' : count}</span>}
      </button>

      {open && (
        <div className="nb__panel">
          <div className="nb__panel-head">
            <span>Notifications</span>
            <button className="nb__link" onClick={() => navigate(allLink)}>View all</button>
          </div>

          {loadingList ? (
            <p className="nb__empty">Loading…</p>
          ) : items.length === 0 ? (
            <p className="nb__empty">No notifications yet.</p>
          ) : (
            <ul className="nb__list">
              {items.slice(0, 20).map((n) => (
                <li
                  key={n.id}
                  className={`nb__item${n.is_read ? '' : ' nb__item--unread'}`}
                  onClick={() => openItem(n)}
                >
                  <div className="nb__item-text">
                    <strong>{n.title}</strong>
                    <p>{n.body}</p>
                  </div>
                  <span className="nb__item-time">{timeAgo(n.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}