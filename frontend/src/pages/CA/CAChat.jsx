import { useEffect, useRef, useState } from 'react';
import api from '../../services/api';
import AppShell from '../../components/AppShell';
import { formatClock, timeAgo } from '../../utils/time';
import './CAChat.css';

export default function CAChat() {
  const [threads, setThreads] = useState([]);
  const [active, setActive] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef(null);

  async function loadThreads() {
    try {
      const res = await api.get('/chat/threads');
      setThreads(res.data.threads || []);
      if (!active && res.data.threads?.length) {
        setActive(res.data.threads[0]);
      }
    } catch {
      setThreads([]);
    }
  }

  async function loadMessages(threadId) {
    if (!threadId) return;
    try {
      const res = await api.get(`/chat/thread/${threadId}`);
      setMessages(res.data.messages || []);
    } catch {
      setMessages([]);
    }
  }

  useEffect(() => { loadThreads(); }, []);
  useEffect(() => { loadMessages(active?.thread_id); }, [active]);

  // Poll the active thread every 5s.
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => loadMessages(active.thread_id), 5000);
    return () => clearInterval(id);
  }, [active]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  async function send(e) {
    e.preventDefault();
    const body = text.trim();
    if (!body || !active) return;
    setBusy(true);
    try {
      await api.post(`/chat/send-to/${active.client_id}`, {
        content: body,
        message_type: 'text',
      });
      setText('');
      await loadMessages(active.thread_id);
      await loadThreads();
    } catch (err) {
      alert(err.response?.data?.message || 'Send failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="ch-wrap">
        <aside className="ch-side">
          <h2 className="ch-side__title">Chats</h2>
          {threads.length === 0 ? (
            <p className="ch-empty">No conversations yet.</p>
          ) : (
            <ul className="ch-threads">
              {threads.map((t) => (
                <li
                  key={t.thread_id}
                  className={`ch-thread${active?.thread_id === t.thread_id ? ' ch-thread--active' : ''}`}
                  onClick={() => setActive(t)}
                >
                  <div className="ch-thread__avatar">
                    {(t.business_name || '?').charAt(0).toUpperCase()}
                  </div>
                  <div className="ch-thread__meta">
                    <p className="ch-thread__name">{t.business_name}</p>
                    <p className="ch-thread__preview">{t.last_message || 'No messages yet'}</p>
                  </div>
                  {t.unread_count > 0 && <span className="ch-thread__badge">{t.unread_count}</span>}
                </li>
              ))}
            </ul>
          )}
        </aside>

        <section className="ch-main">
          {!active ? (
            <div className="ch-nothread">Select a conversation to start chatting.</div>
          ) : (
            <>
              <header className="ch-main__head">
                <div className="ch-thread__avatar ch-thread__avatar--sm">
                  {(active.business_name || '?').charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="ch-main__name">{active.business_name}</p>
                  <p className="ch-main__sub">{active.owner_name}</p>
                </div>
              </header>

              <div className="ch-list">
                {messages.length === 0 ? (
                  <p className="ch-empty">No messages yet. Say hello.</p>
                ) : (
                  messages.map((m) => (
                    <div key={m.id} className={`ch-msg ch-msg--${m.sender_role}`}>
                      <div className="ch-msg__bubble">{m.content}</div>
                      <span className="ch-msg__time">{formatClock(m.created_at)}</span>
                    </div>
                  ))
                )}
                <div ref={bottomRef} />
              </div>

              <form className="ch-input" onSubmit={send}>
                <input
                  type="text"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder={`Message ${active.business_name}…`}
                  disabled={busy}
                />
                <button type="submit" className="ch-send" disabled={busy || !text.trim()}>
                  Send
                </button>
              </form>
            </>
          )}
        </section>
      </div>
    </AppShell>
  );
}