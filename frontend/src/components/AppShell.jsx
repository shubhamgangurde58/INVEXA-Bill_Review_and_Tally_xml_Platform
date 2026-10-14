import { NavLink, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import './AppShell.css';

const RAIL = {
  client: [
    { to: '/client/dashboard', icon: 'grid', label: 'Dashboard' },
    { to: '/client/invoices', icon: 'doc', label: 'Invoices' },
    { to: '/client/chat', icon: 'chat', label: 'Chat' },
    { to: '/client/notifications', icon: 'bell', label: 'Notifications' },
  ],
  ca: [
    { to: '/ca/dashboard', icon: 'grid', label: 'Dashboard' },
    { to: '/ca/clients', icon: 'user', label: 'Clients' },
    { to: '/ca/documents', icon: 'doc', label: 'Documents' },
    { to: '/ca/chat', icon: 'chat', label: 'Chat' },
    { to: '/ca/notifications', icon: 'bell', label: 'Notifications' },
  ],
};

const TABS = {
  client: [
    { to: '/client/dashboard', label: 'Dashboard' },
    { to: '/client/invoices', label: 'Invoices' },
    { to: '/client/chat', label: 'Chat' },
    { to: '/client/notifications', label: 'Notifications' },
  ],
  ca: [
    { to: '/ca/dashboard', label: 'Dashboard' },
    { to: '/ca/clients', label: 'Clients' },
    { to: '/ca/documents', label: 'Documents' },
    { to: '/ca/chat', label: 'Chat' },
  ],
};

function Icon({ name, size = 18 }) {
  const paths = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></>,
    doc: <><path d="M7 3h7l5 5v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1z" /><path d="M14 3v5h5" /></>,
    chat: <><path d="M21 11.5a8.5 8.5 0 01-8.5 8.5c-1.5 0-3-.4-4.3-1L3 21l2-5.2A8.5 8.5 0 1121 11.5z" /></>,
    bell: <><path d="M6 9a6 6 0 1112 0c0 4 1.5 5.5 1.5 5.5H4.5S6 13 6 9z" /><path d="M10 19a2 2 0 004 0" /></>,
    user: <><circle cx="12" cy="8" r="3.5" /><path d="M5 20c0-3.9 3.1-7 7-7s7 3.1 7 7" /></>,
    logout: <><path d="M9 21H6a2 2 0 01-2-2V5a2 2 0 012-2h3" /><path d="M16 17l5-5-5-5" /><path d="M21 12H9" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></>,
    gear: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 00.3 1.9l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.9-.3 1.7 1.7 0 00-1 1.6V21a2 2 0 01-4 0v-.2a1.7 1.7 0 00-1-1.5 1.7 1.7 0 00-1.9.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.9 1.7 1.7 0 00-1.5-1H3a2 2 0 010-4h.2a1.7 1.7 0 001.5-1 1.7 1.7 0 00-.3-1.9l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.9.3H9a1.7 1.7 0 001-1.5V3a2 2 0 014 0v.2a1.7 1.7 0 001 1.5 1.7 1.7 0 001.9-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.9V9a1.7 1.7 0 001.5 1h.2a2 2 0 010 4h-.2a1.7 1.7 0 00-1.5 1z" /></>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  );
}

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const role = user?.role || 'client';

  const [unread, setUnread] = useState(0);
  const [query, setQuery] = useState('');

  useEffect(() => {
  let cancelled = false;
  async function poll() {
    if (document.hidden) return;      // skip if tab hidden
    try {
      const res = await api.get('/notifications/unread-count');
      if (!cancelled) setCount(res.data.count || 0);
    } catch {}
  }
  poll();
  const id = setInterval(poll, 30000);
  return () => { cancelled = true; clearInterval(id); };
}, []);

  function handleLogout() {
    logout();
    navigate(role === 'ca' ? '/ca-login' : '/client/login', { replace: true });
  }

  function submitSearch(e) {
    if (e.key !== 'Enter') return;
    const term = query.trim();
    const target = role === 'ca' ? '/ca/documents' : '/client/invoices';
    navigate(term ? `${target}?q=${encodeURIComponent(term)}` : target);
  }

  const initial = (user?.name || user?.business_name || '?').charAt(0).toUpperCase();
  const displayName = user?.name || user?.business_name || 'User';
  const roleLabel = role === 'ca' ? `CA · ${user?.firm_name || ''}` : 'Shop Owner';

  return (
    <div className="sh">
      <aside className="sh__rail">
        <div className="sh__logo">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="3" width="18" height="18" rx="6" fill="url(#shLogoGrad)" />
            <path d="M8 12.5L10.5 15L16 9" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            <defs>
              <linearGradient id="shLogoGrad" x1="3" y1="3" x2="21" y2="21" gradientUnits="userSpaceOnUse">
                <stop stopColor="#0D9488" /><stop offset="1" stopColor="#2DD4BF" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        <nav className="sh__rail-nav">
          {RAIL[role].map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              title={item.label}
              className={({ isActive }) => `sh__rail-btn${isActive ? ' sh__rail-btn--active' : ''}`}
            >
              <Icon name={item.icon} />
              {item.icon === 'bell' && unread > 0 && <span className="sh__rail-dot" />}
            </NavLink>
          ))}
        </nav>

        <button className="sh__rail-btn sh__rail-logout" onClick={handleLogout} title="Log out">
          <Icon name="logout" />
        </button>
      </aside>

      <div className="sh__body">
        <header className="sh__top">
          <nav className="sh__tabs">
            {TABS[role].map((tab) => (
              <NavLink
                key={tab.to}
                to={tab.to}
                className={({ isActive }) => `sh__tab${isActive ? ' sh__tab--active' : ''}`}
              >
                {tab.label}
              </NavLink>
            ))}
          </nav>

          <div className="sh__top-right">
            <div className="sh__search">
              <Icon name="search" size={15} />
              <input
                type="text"
                placeholder="Search…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={submitSearch}
              />
            </div>

            <button
              className="sh__user"
              onClick={() => navigate(role === 'ca' ? '/ca/profile' : '/client/profile')}
              title={role === 'ca' ? 'View profile' : 'My profile'}
            >
              <span className="sh__avatar">{initial}</span>
              <div className="sh__user-meta">
                <span className="sh__user-name">{displayName}</span>
                <span className="sh__user-role">{roleLabel}</span>
              </div>
            </button>
          </div>
        </header>

        <main className="sh__main">{children}</main>
      </div>
    </div>
  );
}