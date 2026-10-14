import { useEffect, useRef, useState } from 'react';
import api from '../../services/api';
import AppShell from '../../components/AppShell';
import './Chat.css';
import { formatClock } from '../../utils/time';

// Two-pane chat. Left shows the single thread with the CA (clients
// only ever have one conversation — with their firm). Right is the
// message list plus input. Polls every 5 seconds while open.

export default function Chat() {
    const [thread, setThread] = useState(null);
    const [messages, setMessages] = useState([]);
    const [text, setText] = useState('');
    const [busy, setBusy] = useState(false);
    const [loading, setLoading] = useState(true);
    const bottomRef = useRef(null);

    async function loadThread() {
        try {
            const res = await api.get('/chat/my-thread');
            setThread(res.data.thread);
            setMessages(res.data.messages || []);
        } catch {
            // thread may not exist yet — the backend will create on first send
        } finally {
            setLoading(false);
        }
    }

    async function send(e) {
        e.preventDefault();
        const body = text.trim();
        if (!body) return;
        setBusy(true);
        try {
            await api.post('/chat/send', { content: body, message_type: 'text' });
            setText('');
            await loadThread();
        } catch {
            // ignore for now
        } finally {
            setBusy(false);
        }
    }

    useEffect(() => {
        loadThread();
        const id = setInterval(loadThread,8000);
        return () => clearInterval(id);
    }, []);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages.length]);

    return (
        <AppShell>
            <div className="ch-wrap">
                <aside className="ch-side">
                    <div className="ch-side__head">
                        <span className="ch-side__avatar">CA</span>
                        <div>
                            <p className="ch-side__name">Your CA</p>
                            <p className="ch-side__sub">Chartered Accountant</p>
                        </div>
                    </div>
                    <p className="ch-side__hint">
                        Ask questions about your bills, send photos, or share a specific invoice.
                    </p>
                </aside>

                <section className="ch-main">
                    <div className="ch-list">
                        {loading ? (
                            <p className="ch-empty">Loading…</p>
                        ) : messages.length === 0 ? (
                            <p className="ch-empty">No messages yet. Say hello 👋</p>
                        ) : (
                            messages.map((m) => (
                                <div key={m.id} className={`ch-msg ch-msg--${m.sender_role}`}>
                                    <div className="ch-msg__bubble">{m.content}</div>
                                    <span className="ch-msg__time">
                                        {formatClock(m.created_at)}
                                    </span>
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
                            placeholder="Write a message…"
                            disabled={busy}
                        />
                        <button type="submit" className="ch-send" disabled={busy || !text.trim()}>
                            Send
                        </button>
                    </form>
                </section>
            </div>
        </AppShell>
    );
}