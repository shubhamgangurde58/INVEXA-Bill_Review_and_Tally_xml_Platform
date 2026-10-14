import { createContext, useContext, useEffect, useState } from 'react';
import { clearSession, getUserFromStorage, setSession } from '../services/api';

// Auth state lives here so any page can ask "who is logged in?"
// without prop drilling. The user object is also cached in
// localStorage so a page refresh keeps the session alive.

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore the session from storage on first mount. We do not call
  // /auth/me here — that would block the first paint. If the token
  // has expired, the first API call will return 401 and the route
  // guard will send the user back to login.
  useEffect(() => {
    const saved = getUserFromStorage();
    if (saved) setUser(saved);
    setLoading(false);
  }, []);

  // Called by the login and signup pages after a successful request.
  function saveSession(token, nextUser) {
    setSession(token, nextUser);
    setUser(nextUser);
  }

  // Called by the logout button. The backend has no session to end
  // because tokens are stateless; clearing local storage is enough.
  function logout() {
    clearSession();
    setUser(null);
  }

  // Used by the client dashboard to refresh status after the CA
  // approves a pending account, without a full reload.
  function updateUser(partial) {
    const nextUser = { ...user, ...partial };
    setSession(localStorage.getItem('invexa_token'), nextUser);
    setUser(nextUser);
  }

  return (
    <AuthContext.Provider
      value={{ user, loading, saveSession, logout, updateUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return ctx;
}