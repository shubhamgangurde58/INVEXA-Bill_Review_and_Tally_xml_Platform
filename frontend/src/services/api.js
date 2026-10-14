import axios from 'axios';

// Every network call goes through this one client so the JWT is
// attached in one place and the JSON envelope from the backend
// ({status, data} on success, {status, message} on error) is
// returned consistently everywhere.

const TOKEN_KEY = 'invexa_token';
const USER_KEY  = 'invexa_user';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000/api',
  headers: { 'Content-Type': 'application/json' },
});

// Attach the JWT to every request if we have one.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Return response.data directly so pages write `res.data` instead of
// `res.data.data`. On 401 (expired or missing token) we clear local
// storage but do not redirect here — the route guard does that, so
// the user is not bounced out mid-form.
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
    return Promise.reject(error);
  }
);

export const getToken = () => localStorage.getItem(TOKEN_KEY);

export const setSession = (token, user) => {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
};

export const clearSession = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

export const getUserFromStorage = () => {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
};

export default api;