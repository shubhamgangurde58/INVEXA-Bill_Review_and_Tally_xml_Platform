import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';

import InvexaLanding from './pages/Landing/InvexaLanding';
import RoleSelect from './pages/RoleSelect/RoleSelect';

import ClientSignup from './pages/Client/Signup';
import ClientLogin from './pages/Client/Login';
import ClientForgot from './pages/Client/ForgotPassword';
import ClientReset from './pages/Client/ResetPassword';
import ClientDashboard from './pages/Client/Dashboard';
import ClientInvoices from './pages/Client/Invoices';
import ClientNotifications from './pages/Client/Notifications';
import ClientChat from './pages/Client/Chat';

import CASignup from './pages/CA/CASignup';
import CALogin from './pages/CA/CALogin';
import CADashboard from './pages/CA/CADashboard';
import CAClients from './pages/CA/CAClients';
import CADocuments from './pages/CA/CADocuments';
import CAChat from './pages/CA/CAChat';
import CANotifications from './pages/CA/CANotifications';
import CAProfile from './pages/CA/CAProfile';
import Profile from './pages/Client/Profile';


export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<InvexaLanding />} />
          <Route path="/role-select" element={<RoleSelect />} />

          <Route path="/signup" element={<ClientSignup />} />
          <Route path="/login" element={<ClientLogin />} />
          <Route path="/forgot-password" element={<ClientForgot />} />
          <Route path="/reset-password" element={<ClientReset />} />
          <Route path="/ca-signup" element={<CASignup />} />
          <Route path="/ca-login" element={<CALogin />} />

          <Route path="/dashboard" element={<ProtectedRoute role="client"><ClientDashboard /></ProtectedRoute>} />
          <Route path="/client/dashboard" element={<ProtectedRoute role="client"><ClientDashboard /></ProtectedRoute>} />
          <Route path="/client/invoices" element={<ProtectedRoute role="client"><ClientInvoices /></ProtectedRoute>} />
          <Route path="client/profile" element={<ProtectedRoute role="client"><Profile /></ProtectedRoute>}/>
          <Route path="/client/notifications" element={<ProtectedRoute role="client"><ClientNotifications /></ProtectedRoute>} />
          <Route path="/client/chat" element={<ProtectedRoute role="client"><ClientChat /></ProtectedRoute>} />

          <Route path="/ca/dashboard" element={<ProtectedRoute role="ca"><CADashboard /></ProtectedRoute>} />
          <Route path="/ca/clients" element={<ProtectedRoute role="ca"><CAClients /></ProtectedRoute>} />
          <Route path="/ca/documents" element={<ProtectedRoute role="ca"><CADocuments /></ProtectedRoute>} />
          <Route path="/ca/profile" element={<ProtectedRoute role="ca"><CAProfile /></ProtectedRoute>} />
          <Route path="/ca/chat" element={<ProtectedRoute role="ca"><CAChat /></ProtectedRoute>} />
          <Route path="/ca/notifications" element={<ProtectedRoute role="ca"><CANotifications /></ProtectedRoute>} />
          <Route path="/ca/profile" element={<ProtectedRoute role="ca"><CAProfile /></ProtectedRoute>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}