import { useEffect, useState } from 'react';
import api from '../../services/api';
import AppShell from '../../components/AppShell';
import { useAuth } from '../../context/AuthContext';
import { formatDateTime } from '../../utils/time';
import './Profile.css';

// Client profile: read-only personal + business details plus the
// firm/CA they are connected to. Edits are limited to fields the
// backend supports today (business name, owner name, mobile, address).
export default function Profile() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [firm, setFirm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [edit, setEdit] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    business_name: '',
    owner_name: '',
    mobile: '',
    address: '',
  });

  async function load() {
    setLoading(true);
    try {
      const [p, f] = await Promise.all([
        api.get('/client/get-profile'),
        api.get('/client/get-my-firm'),
      ]);
      setProfile(p.data);
      setFirm(f.data);
      setForm({
        business_name: p.data.business_name || '',
        owner_name: p.data.owner_name || '',
        mobile: p.data.mobile || '',
        address: p.data.address || '',
      });
    } catch (err) {
      console.error('Profile load failed:', err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function save() {
    setBusy(true);
    try {
      await api.put('/client/update-profile', form);
      await load();
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

  const initial = (profile?.business_name || '?').charAt(0).toUpperCase();

  return (
    <AppShell>
      <h1 className="cp-title">My profile</h1>
      <p className="cp-sub">Your account, business details and the CA you work with.</p>

      {/* Identity card */}
      <section className="cp-card cp-card--identity">
        <div className="cp-avatar">{initial}</div>
        <div className="cp-identity">
          <h2 className="cp-identity__name">{profile.business_name}</h2>
          <p className="cp-identity__owner">{profile.owner_name}</p>
          <p className="cp-identity__email">{profile.email}</p>
        </div>
        <span className={`cp-status cp-status--${profile.status}`}>
          {profile.status === 'active' ? 'Active' :
           profile.status === 'pending' ? 'Pending approval' :
           'Not approved'}
        </span>
      </section>

      {/* Business details */}
      <section className="cp-card">
        <div className="cp-card__head">
          <h2 className="cp-card__title">Business details</h2>
          {!edit && (
            <button className="cp-btn cp-btn--ghost" onClick={() => setEdit(true)}>
              Edit
            </button>
          )}
        </div>

        <div className="cp-grid">
          <label className="cp-field">
            <span>Business name</span>
            <input
              type="text"
              value={form.business_name}
              onChange={(e) => setForm({ ...form, business_name: e.target.value })}
              disabled={!edit}
            />
          </label>
          <label className="cp-field">
            <span>Owner name</span>
            <input
              type="text"
              value={form.owner_name}
              onChange={(e) => setForm({ ...form, owner_name: e.target.value })}
              disabled={!edit}
            />
          </label>
          <label className="cp-field">
            <span>Mobile</span>
            <input
              type="tel"
              value={form.mobile}
              onChange={(e) => setForm({ ...form, mobile: e.target.value })}
              disabled={!edit}
              maxLength={10}
            />
          </label>
          <label className="cp-field">
            <span>Email</span>
            <div className="cp-static">{profile.email}</div>
          </label>
          <label className="cp-field">
            <span>GSTIN</span>
            <div className="cp-static">{profile.gstin || '—'}</div>
          </label>
          <label className="cp-field cp-field--full">
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
          <div className="cp-save">
            <button className="cp-btn cp-btn--ghost" onClick={() => { setEdit(false); load(); }}>
              Cancel
            </button>
            <button className="cp-btn cp-btn--primary" onClick={save} disabled={busy}>
              {busy ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        )}
      </section>

      {/* Connected CA */}
      <section className="cp-card">
        <h2 className="cp-card__title">Your CA</h2>
        {!firm ? (
          <p className="cp-muted">No CA connected.</p>
        ) : (
          <div className="cp-firm">
            <span className="cp-firm__avatar">{firm.ca_name?.charAt(0).toUpperCase()}</span>
            <div>
              <p className="cp-firm__name">{firm.ca_name}</p>
              <p className="cp-firm__meta">
                {firm.firm_name}
                {firm.ca_membership_number ? ` · ICAI ${firm.ca_membership_number}` : ''}
              </p>
            </div>
          </div>
        )}
      </section>

      {/* Account info */}
      <section className="cp-card">
        <h2 className="cp-card__title">Account</h2>
        <div className="cp-grid">
          <div className="cp-field">
            <span>Joined</span>
            <div className="cp-static">
              {profile.joined_at ? formatDateTime(profile.joined_at) : '—'}
            </div>
          </div>
          <div className="cp-field">
            <span>Email verified</span>
            <div className="cp-static">{profile.email_verified ? 'Yes' : 'No'}</div>
          </div>
        </div>
      </section>
    </AppShell>
  );
}