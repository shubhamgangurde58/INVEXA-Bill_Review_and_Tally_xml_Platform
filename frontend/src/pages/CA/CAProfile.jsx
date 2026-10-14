import { useEffect, useState } from 'react';
import api from '../../services/api';
import AppShell from '../../components/AppShell';
import { useAuth } from '../../context/AuthContext';
import './CAProfile.css';

// Where the CA sees and manages their firm's invite code, plus
// edit their firm name, GSTIN and address. This page replaces the
// code card that used to sit on the CA dashboard.
export default function CAProfile() {
  const { user } = useAuth();
  const [firm, setFirm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [edit, setEdit] = useState(false);
  const [form, setForm] = useState({ name: '', gstin: '', address: '' });

  async function load() {
    setLoading(true);
    try {
      const res = await api.get('/firm/get-profile');
      setFirm(res.data);
      setForm({
        name: res.data.name || '',
        gstin: res.data.gstin || '',
        address: res.data.address || '',
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function copyCode() {
    if (!firm) return;
    navigator.clipboard.writeText(firm.invite_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function regenerate() {
    if (!window.confirm('Regenerate the invite code? Clients with the old code cannot sign up anymore. Existing clients are not affected.')) return;
    setBusy(true);
    try {
      const res = await api.post('/firm/regenerate-invite-code');
      setFirm((p) => ({ ...p, invite_code: res.data.invite_code }));
    } catch {
      alert('Could not regenerate. Try again.');
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    setBusy(true);
    try {
      const res = await api.put('/firm/update-profile', form);
      setFirm(res.data);
      setEdit(false);
    } catch (err) {
      alert(err.response?.data?.message || 'Save failed.');
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <AppShell><p style={{ padding: 40, color: '#64748B' }}>Loading…</p></AppShell>;
  }

  return (
    <AppShell>
      <h1 className="pf-title">Firm profile</h1>
      <p className="pf-sub">Your firm details and the invite code your clients use to join.</p>

      {/* Invite code */}
      <section className="pf-card pf-card--code">
        <div>
          <p className="pf-label">Invite code</p>
          <p className="pf-code">{firm?.invite_code}</p>
          <p className="pf-hint">
            Share this with clients. They enter it during signup and you
            approve each one from the Clients page.
          </p>
        </div>
        <div className="pf-actions">
          <button className="pf-btn pf-btn--ghost" onClick={copyCode}>
            {copied ? 'Copied' : 'Copy code'}
          </button>
          <button className="pf-btn pf-btn--ghost" onClick={regenerate} disabled={busy}>
            Regenerate
          </button>
        </div>
      </section>

      {/* Firm details */}
      <section className="pf-card">
        <div className="pf-card__head">
          <h2 className="pf-card__title">Firm details</h2>
          {!edit && (
            <button className="pf-btn pf-btn--ghost" onClick={() => setEdit(true)}>Edit</button>
          )}
        </div>

        <div className="pf-grid">
          <label className="pf-field">
            <span>Firm name</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              disabled={!edit}
            />
          </label>
          <label className="pf-field">
            <span>GSTIN</span>
            <input
              type="text"
              value={form.gstin}
              onChange={(e) => setForm({ ...form, gstin: e.target.value.toUpperCase() })}
              disabled={!edit}
              maxLength={15}
            />
          </label>
          <label className="pf-field pf-field--full">
            <span>Address</span>
            <input
              type="text"
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
              disabled={!edit}
            />
          </label>
        </div>

        {edit && (
          <div className="pf-save">
            <button className="pf-btn pf-btn--ghost" onClick={() => { setEdit(false); load(); }}>Cancel</button>
            <button className="pf-btn pf-btn--primary" onClick={save} disabled={busy}>
              {busy ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        )}
      </section>

      {/* Account */}
      <section className="pf-card">
        <h2 className="pf-card__title">Account</h2>
        <div className="pf-grid">
          <div className="pf-field">
            <span>Name</span>
            <div className="pf-static">{user?.name}</div>
          </div>
          <div className="pf-field">
            <span>Email</span>
            <div className="pf-static">{user?.email}</div>
          </div>
        </div>
      </section>
    </AppShell>
  );
}