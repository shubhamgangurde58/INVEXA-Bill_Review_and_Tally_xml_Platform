import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import './CALogin.css';

// CA login. Identical layout to signup so the two screens feel like
// a pair. On success, the CA is sent to whichever CA page they tried
// to open (or the dashboard by default).

export default function CALogin() {
  const navigate = useNavigate();
  const location = useLocation();
  const { saveSession } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      const res = await api.post('/auth/login', {
        email,
        password,
        role: 'ca',
      });
      saveSession(res.data.token, res.data.user);

      const from = location.state?.from || '/ca/dashboard';
      navigate(from, { replace: true });
    } catch (err) {
      const message = err.response?.data?.message || 'Login failed. Check your email and password.';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <aside className="auth-side auth-side--login">
        <Link to="/" className="auth-side__logo">Invexa</Link>

        <div className="auth-side__content">
          <span className="eyebrow">Chartered Accountants</span>
          <h2>Sign in to your firm.</h2>
          <p>
            Review your clients' bills, approve the ones that are ready,
            and hand back a Tally-ready file — all from one screen.
          </p>
        </div>
      </aside>

      <main className="auth-main">
        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <header className="auth-form__head">
            <h1>Welcome back</h1>
            <p>Sign in to continue to your dashboard.</p>
          </header>

          {error && <div className="auth-error">{error}</div>}

          <label className="auth-field">
            <span className="auth-field__label">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@firm.com"
              autoComplete="email"
              required
            />
          </label>

          <label className="auth-field">
            <span className="auth-field__label">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
              autoComplete="current-password"
              required
            />
          </label>

          <button type="submit" className="auth-submit" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>

          <p className="auth-form__footer">
            New to Invexa? <Link to="/ca-signup">Create a firm account</Link>
          </p>
        </form>
      </main>
    </div>
  );
}