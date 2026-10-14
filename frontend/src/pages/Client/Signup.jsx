import { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import './Signup.css';

// Shop owner signup. Two steps: verify the firm's invite code, then
// fill in business details. On success the client is NOT logged in —
// their account sits as "pending" until the CA approves it. This is
// what makes a leaked invite code useless on its own.
export default function Signup() {
  const [inviteCode, setInviteCode] = useState('');
  const [firmName, setFirmName] = useState('');
  const [checkingCode, setCheckingCode] = useState(false);
  const [codeError, setCodeError] = useState('');

  const [form, setForm] = useState({
    business_name: '',
    owner_name: '',
    email: '',
    mobile: '',
    gstin: '',
    address: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(null);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function checkCode() {
    setCodeError(''); setFirmName('');
    const code = inviteCode.trim().toUpperCase();
    if (!code) { setCodeError('Enter an invite code'); return; }
    setCheckingCode(true);
    try {
      const res = await api.get(`/auth/invite-lookup?code=${encodeURIComponent(code)}`);
      setFirmName(res.data.firm_name);
    } catch (err) {
      setCodeError(err.response?.data?.message || 'Invalid invite code');
    } finally {
      setCheckingCode(false);
    }
  }

  async function submit(e) {
    e.preventDefault();
    if (!firmName) { setError('Please verify the invite code first'); return; }
    setError(''); setSubmitting(true);
    try {
      const res = await api.post('/auth/signup-client', {
        invite_code: inviteCode.trim().toUpperCase(),
        ...form,
      });
      setSuccess({ firmName: res.data.firm_name });
    } catch (err) {
      setError(err.response?.data?.message || 'Could not create your account.');
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <div className="auth-page">
        <aside className="auth-side">
          <Link to="/" className="auth-side__logo">Invexa</Link>
          <div className="auth-side__illustration">
            <div className="auth-side__avatar">
              <svg width="120" height="150" viewBox="0 0 120 150" fill="none">
                <circle cx="60" cy="38" r="26" fill="url(#avatarHead)" />
                <path d="M18 150v-24c0-23 19-42 42-42s42 19 42 42v24H18z" fill="url(#avatarBody)" />
                <defs>
                  <linearGradient id="avatarHead" x1="34" y1="12" x2="86" y2="64" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#FBCFA0" /><stop offset="1" stopColor="#F4B983" />
                  </linearGradient>
                  <linearGradient id="avatarBody" x1="18" y1="84" x2="102" y2="150" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#0D9488" /><stop offset="1" stopColor="#14B8A6" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
          </div>
        </aside>

        <main className="auth-main">
          <div className="auth-form auth-form--wide" style={{ textAlign: 'center', maxWidth: 480 }}>
            <div style={{
              width: 72, height: 72, borderRadius: '50%',
              background: 'linear-gradient(135deg, #0D9488, #2DD4BF)',
              display: 'grid', placeItems: 'center',
              margin: '0 auto 24px',
              boxShadow: '0 16px 40px rgba(13,148,136,0.35)',
            }}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
                   stroke="white" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12l5 5L20 7" />
              </svg>
            </div>
            <h1 className="auth-form__title">Request sent</h1>
            <p className="auth-form__desc" style={{ marginBottom: 8 }}>
              <strong>{success.firmName}</strong> has been notified.
            </p>
            <p className="auth-form__desc" style={{ marginBottom: 28 }}>
              You can sign in once your CA approves your account. We'll send you
              a confirmation by email.
            </p>
            <Link to="/login" className="auth-submit" style={{ display: 'inline-flex', width: 'auto', padding: '14px 32px' }}>
              Go to sign in
            </Link>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <aside className="auth-side">
        <Link to="/" className="auth-side__logo">Invexa</Link>

        <div className="auth-side__illustration">
          <div className="auth-side__avatar">
            <svg width="120" height="150" viewBox="0 0 120 150" fill="none">
              <circle cx="60" cy="38" r="26" fill="url(#avatarHeadSU)" />
              <path d="M18 150v-24c0-23 19-42 42-42s42 19 42 42v24H18z" fill="url(#avatarBodySU)" />
              <rect x="70" y="80" width="30" height="42" rx="4" fill="#ffffff" opacity="0.9" transform="rotate(8 70 80)" />
              <defs>
                <linearGradient id="avatarHeadSU" x1="34" y1="12" x2="86" y2="64" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#FBCFA0" /><stop offset="1" stopColor="#F4B983" />
                </linearGradient>
                <linearGradient id="avatarBodySU" x1="18" y1="84" x2="102" y2="150" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#0D9488" /><stop offset="1" stopColor="#14B8A6" />
                </linearGradient>
              </defs>
            </svg>
          </div>
        </div>
      </aside>

      <main className="auth-main">
        <form className="auth-form auth-form--wide" onSubmit={submit} noValidate>
          <h1 className="auth-form__title">Create your account</h1>
          <p className="auth-form__desc">
            Ask your CA for the invite code, then fill in your business details.
          </p>

          {/* Step 1: invite code */}
          <div className="auth-code-row">
            <label className="auth-field auth-field--grow">
              <span className="auth-field__label">Firm Invite Code</span>
              <input
                type="text"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                placeholder="KULK-4A8F2"
                maxLength={12}
                required
              />
            </label>
            <button
              type="button"
              className="auth-code-btn"
              onClick={checkCode}
              disabled={checkingCode}
            >
              {checkingCode ? 'Checking…' : 'Verify'}
            </button>
          </div>

          {codeError && <div className="auth-error">{codeError}</div>}
          {firmName && (
            <div className="auth-ok">
              Joining <strong>{firmName}</strong>
            </div>
          )}

          {/* Step 2: details, revealed after the code is confirmed */}
          {firmName && (
            <>
              <div className="auth-grid">
                <label className="auth-field">
                  <span className="auth-field__label">Business Name</span>
                  <input
                    type="text"
                    value={form.business_name}
                    onChange={(e) => update('business_name', e.target.value)}
                    placeholder="Sharma General Store"
                    required
                  />
                </label>

                <label className="auth-field">
                  <span className="auth-field__label">Owner Name</span>
                  <input
                    type="text"
                    value={form.owner_name}
                    onChange={(e) => update('owner_name', e.target.value)}
                    placeholder="Ramesh Sharma"
                    autoComplete="name"
                    required
                  />
                </label>

                <label className="auth-field auth-field--full">
                  <span className="auth-field__label">Email</span>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => update('email', e.target.value)}
                    placeholder="you@shop.com"
                    autoComplete="email"
                    required
                  />
                </label>

                <label className="auth-field">
                  <span className="auth-field__label">Mobile</span>
                  <input
                    type="tel"
                    value={form.mobile}
                    onChange={(e) => update('mobile', e.target.value)}
                    placeholder="9876543210"
                    inputMode="numeric"
                    maxLength={10}
                    autoComplete="tel"
                    required
                  />
                </label>

                <label className="auth-field">
                  <span className="auth-field__label">GSTIN (optional)</span>
                  <input
                    type="text"
                    value={form.gstin}
                    onChange={(e) => update('gstin', e.target.value.toUpperCase())}
                    placeholder="27AAAAA0000A1Z5"
                    maxLength={15}
                  />
                </label>

                <label className="auth-field auth-field--full">
                  <span className="auth-field__label">Address (optional)</span>
                  <input
                    type="text"
                    value={form.address}
                    onChange={(e) => update('address', e.target.value)}
                    placeholder="Shop 5, FC Road, Pune"
                  />
                </label>

                <label className="auth-field auth-field--full">
                  <span className="auth-field__label">Password</span>
                  <input
                    type="password"
                    value={form.password}
                    onChange={(e) => update('password', e.target.value)}
                    placeholder="8+ chars, one uppercase, one number, one symbol"
                    autoComplete="new-password"
                    required
                  />
                </label>
              </div>

              {error && <div className="auth-error">{error}</div>}

              <button type="submit" className="auth-submit" disabled={submitting}>
                {submitting ? 'Sending request…' : 'Send request to my CA'}
              </button>
            </>
          )}

          <p className="auth-form__footer">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </form>
      </main>
    </div>
  );
}