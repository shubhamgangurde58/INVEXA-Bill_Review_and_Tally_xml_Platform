import { useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import api from '../../services/api';
import './ForgotPassword.css';

// User lands here from the emailed reset link (URL has ?token=...).
// They set a new password, then are sent back to /login.
export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const navigate = useNavigate();

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(e) {
    e.preventDefault();
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setBusy(true); setError('');
    try {
      await api.post('/auth/reset-password', {
        token,
        new_password: password,
      });
      alert('Password updated. Please sign in.');
      navigate('/login', { replace: true });
    } catch (err) {
      setError(err.response?.data?.message || 'Could not reset password.');
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <div className="fp-page">
        <main className="fp-main">
          <div className="fp-card">
            <h1 className="fp-card__title">Link is invalid</h1>
            <p className="fp-card__desc">This reset link is missing its token.</p>
            <Link to="/forgot-password" className="fp-back">Request a new link</Link>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="fp-page">
      <header className="fp-nav">
        <Link to="/" className="fp-nav__logo">Invexa</Link>
      </header>

      <main className="fp-main">
        <div className="fp-card">
          <span className="fp-card__icon">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              <rect x="4" y="10" width="16" height="10" rx="2" />
              <path d="M8 10V7a4 4 0 018 0v3" />
            </svg>
          </span>

          <h1 className="fp-card__title">Set a new password</h1>
          <p className="fp-card__desc">
            8+ characters, one uppercase, one number, one symbol.
          </p>

          <form onSubmit={submit}>
            <label className="fp-field">
              <span className="fp-field__label">New password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter new password"
                autoComplete="new-password"
                required
              />
            </label>
            <label className="fp-field">
              <span className="fp-field__label">Confirm password</span>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="Re-enter password"
                autoComplete="new-password"
                required
              />
            </label>

            {error && <div className="fp-error">{error}</div>}

            <button type="submit" className="fp-submit" disabled={busy}>
              {busy ? 'Updating…' : 'Update password'}
            </button>

            <Link to="/login" className="fp-back">Back to sign in</Link>
          </form>
        </div>
      </main>
    </div>
  );
}