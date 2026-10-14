import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import './CASignup.css';

// CA registration: the CA's own details plus the firm name they are
// creating. On success the backend creates the firm and returns a
// token, so the CA lands on the dashboard already signed in.

const INITIAL = {
  firm_name: '',
  name: '',
  email: '',
  membership_number: '',
  password: '',
};

export default function CASignup() {
  const navigate = useNavigate();
  const { saveSession } = useAuth();

  const [form, setForm] = useState(INITIAL);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      // The API client unwraps { status, data } already, so `res.data`
      // is the payload we need.
      const res = await api.post('/auth/signup-ca', form);
      saveSession(res.data.token, res.data.user);
      navigate('/ca/dashboard', { replace: true });
    } catch (err) {
      const message = err.response?.data?.message || 'Could not create your account. Try again.';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <aside className="auth-side">
        <Link to="/" className="auth-side__logo">Invexa</Link>

        <div className="auth-side__content">
          <span className="eyebrow">For Chartered Accountants</span>
          <h2>Run your practice from one place.</h2>
          <p>
            Get an invite code your clients use to join. Review bills, correct OCR data,
            approve, and export Tally-ready XML — without a single sheet of paper.
          </p>

          <ul className="auth-side__points">
            <li>One firm, one dashboard, unlimited clients</li>
            <li>Invite code controls who can join</li>
            <li>Every bill reviewed before it reaches Tally</li>
          </ul>
        </div>
      </aside>

      <main className="auth-main">
        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <header className="auth-form__head">
            <h1>Create your firm</h1>
            <p>Set up your CA account. Takes about a minute.</p>
          </header>

          {error && <div className="auth-error">{error}</div>}

          <label className="auth-field">
            <span className="auth-field__label">Firm Name</span>
            <input
              type="text"
              value={form.firm_name}
              onChange={(e) => update('firm_name', e.target.value)}
              placeholder="Kulkarni and Associates"
              autoComplete="organization"
              required
            />
          </label>

          <label className="auth-field">
            <span className="auth-field__label">Your Full Name</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => update('name', e.target.value)}
              placeholder="Anil Kulkarni"
              autoComplete="name"
              required
            />
          </label>

          <label className="auth-field">
            <span className="auth-field__label">Work Email</span>
            <input
              type="email"
              value={form.email}
              onChange={(e) => update('email', e.target.value)}
              placeholder="you@firm.com"
              autoComplete="email"
              required
            />
          </label>

          <label className="auth-field">
            <span className="auth-field__label">ICAI Membership Number</span>
            <input
              type="text"
              value={form.membership_number}
              onChange={(e) => update('membership_number', e.target.value)}
              placeholder="123456"
              inputMode="numeric"
              required
            />
          </label>

          <label className="auth-field">
            <span className="auth-field__label">Password</span>
            <input
              type="password"
              value={form.password}
              onChange={(e) => update('password', e.target.value)}
              placeholder="At least 8 characters, one uppercase, one number"
              autoComplete="new-password"
              required
            />
          </label>

          <button type="submit" className="auth-submit" disabled={submitting}>
            {submitting ? 'Creating…' : 'Create firm account'}
          </button>

          <p className="auth-form__footer">
            Already have an account? <Link to="/ca-login">Sign in</Link>
          </p>
        </form>
      </main>
    </div>
  );
}