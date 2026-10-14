import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

// Block a page until the user is signed in with the right role.
// role="ca" protects CA pages, role="client" protects client pages.
// If you leave role undefined it just requires any signed-in user.

const LOGIN_BY_ROLE = {
  ca: '/ca-login',
  client: '/client/login',
};

const HOME_BY_ROLE = {
  ca: '/ca/dashboard',
  client: '/client/dashboard',
};

export default function ProtectedRoute({ role, children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  // First paint: we do not yet know if the session is valid.
  if (loading) {
    return (
      <div style={{ padding: 60, textAlign: 'center', color: '#64748B' }}>
        Loading…
      </div>
    );
  }

  // Not signed in: send them to the correct login page, remembering
  // where they wanted to go so we can send them back after login.
  if (!user) {
    const target = LOGIN_BY_ROLE[role] || '/role-select';
    return <Navigate to={target} state={{ from: location.pathname }} replace />;
  }

  // Signed in but with the wrong role (a client opening a CA page).
  // Send them to their own home rather than a blank error page.
  if (role && user.role !== role) {
    const home = HOME_BY_ROLE[user.role] || '/role-select';
    return <Navigate to={home} replace />;
  }

  return children;
}