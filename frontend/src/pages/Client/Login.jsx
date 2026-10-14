import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import './Login.css';

// Client login. The backend rejects pending or rejected accounts with
// a clear message. Clients who try to sign in early are told to wait
// for their CA's approval.
export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { saveSession } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError(''); setSubmitting(true);
    try {
      const res = await api.post('/auth/login', { email, password, role: 'client' });
      saveSession(res.data.token, res.data.user);
      const from = location.state?.from || '/dashboard';
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed.');
    } finally {
      setSubmitting(false);
    }
  }

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
        <form className="auth-form" onSubmit={submit} noValidate>
          <h1 className="auth-form__title">Welcome back</h1>
          <p className="auth-form__desc">Sign in to your shop account.</p>

          {error && <div className="auth-error">{error}</div>}

          <label className="auth-field">
            <span className="auth-field__label">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@shop.com"
              autoComplete="email"
              required
            />
          </label>

          <label className="auth-field">
            <span className="auth-field__label-row">
              <span className="auth-field__label">Password</span>
              <Link to="/forgot-password" className="auth-field__link">Forgot password?</Link>
            </span>
            <span className="auth-field__input-wrap">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Your password"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="auth-field__eye"
                onClick={() => setShowPassword((v) => !v)}
              >
                {showPassword ? '🙈' : '👁'}
              </button>
            </span>
          </label>

          <button type="submit" className="auth-submit" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>

          <p className="auth-form__footer">
            New to Invexa? <Link to="/signup">Create an account</Link>
          </p>
        </form>
      </main>
    </div>
  );
}