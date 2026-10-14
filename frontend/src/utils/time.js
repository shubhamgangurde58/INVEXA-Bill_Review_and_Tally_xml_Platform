// Shared time helpers. Backend returns UTC timestamps without a timezone
// marker; adding Z before parsing stops the browser from reading them
// as local time (which caused a 5.5 hour drift in IST).

function parseUtc(iso) {
  if (!iso) return null;
  let s = String(iso);
  if (!/[zZ]$/.test(s) && !/[+\-]\d{2}:?\d{2}$/.test(s)) s += 'Z';
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function timeAgo(iso) {
  const d = parseUtc(iso);
  if (!d) return '';
  const diff = (Date.now() - d.getTime()) / 1000;

  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;

  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';

  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
}

export function formatDate(iso) {
  const d = parseUtc(iso);
  if (!d) return '—';
  return d.toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

export function formatDateTime(iso) {
  const d = parseUtc(iso);
  if (!d) return '—';
  const day = d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
  const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  return `${day}, ${time}`;
}

export function formatClock(iso) {
  const d = parseUtc(iso);
  if (!d) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Full local timestamp, used in tooltips on hover.
export function formatFull(iso) {
  const d = parseUtc(iso);
  if (!d) return '';
  return d.toLocaleString();
}