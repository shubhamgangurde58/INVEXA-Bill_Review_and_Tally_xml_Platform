import { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import './ForgotPassword.css';

// Sends a reset link. The backend prints the reset token to the server
// console (email service not wired yet), so during development the CA
// or client reads the link from the terminal. Always shows the same
// message whether or not the email exists, so nobody can enumerate
// registered accounts by watching the response.
export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      await api.post('/auth/forgot-password', { email });
      setSent(true);
    } catch (err) {
      setError(err.response?.data?.message || 'Could not send reset email.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fp-page">
      <header className="fp-nav">
        <Link to="/" className="fp-nav__logo">Invexa</Link>
        <Link to="/login" className="btn-sign-in">Sign in</Link>
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

          <h1 className="fp-card__title">Forgot password?</h1>
          <p className="fp-card__desc">
            Enter your registered email. We'll send a link to reset it.
          </p>

          {sent ? (
            <>
              <div className="fp-success">
                <strong>Check your inbox.</strong> If that email is registered,
                a reset link has been sent.
              </div>
              <p className="fp-hint">
                During development, the link appears in the backend terminal
                (search for <code>[DEV ONLY]</code>).
              </p>
              <Link to="/login" className="fp-back">Back to sign in</Link>
            </>
          ) : (
            <form onSubmit={submit}>
              <label className="fp-field">
                <span className="fp-field__label">Email address</span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  autoComplete="email"
                  required
                />
              </label>

              {error && <div className="fp-error">{error}</div>}

              <button type="submit" className="fp-submit" disabled={busy}>
                {busy ? 'Sending…' : 'Send reset link'}
              </button>

              <Link to="/login" className="fp-back">Back to sign in</Link>
            </form>
          )}
        </div>
      </main>

      <footer className="fp-footer">
        <span className="fp-footer__logo">Invexa</span>
        <span className="fp-footer__copy">© {new Date().getFullYear()} Invexa. All rights reserved.</span>
      </footer>
    </div>
  );
}