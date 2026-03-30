import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Navbar from './components/Navbar';
import Layout from './components/Layout';
import Home from './components/Home';
import Dashboard from './components/Dashboard';
import SkillPrep from './components/SkillPrep';
import MockInterview from './components/MockInterview';
import AIAssistant from './components/AIAssistant';
import Login from './components/auth/Login';
import Signup from './components/auth/Signup';
import VerifyEmail from './components/auth/VerifyEmail';
import ForgotPassword from './components/auth/ForgotPassword';
import ResetPassword from './components/auth/ResetPassword';
import Profile from './components/auth/Profile';
import GoogleCallback from './components/auth/GoogleCallback';
import './App.css';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { authenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner">Loading...</div>
      </div>
    );
  }

  return authenticated ? children : <Navigate to="/login" replace />;
};

// Public Route Component (redirects to home if already logged in)
const PublicRoute = ({ children }) => {
  const { authenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner">Loading...</div>
      </div>
    );
  }

  return authenticated ? <Navigate to="/" replace /> : children;
};

function App() {
  return (
    <AuthProvider>
      <Router
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <div className="App">
          <Routes>
            <Route path="/" element={<><Navbar /><Home /></>} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Layout><Dashboard /></Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/skill-prep"
              element={
                <ProtectedRoute>
                  <Layout><SkillPrep /></Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/mock-interview"
              element={
                <ProtectedRoute>
                  <Layout><MockInterview /></Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/interview-prep"
              element={
                <ProtectedRoute>
                  <Navigate to="/skill-prep" replace />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <Layout><Profile /></Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/ai-assistant"
              element={
                <ProtectedRoute>
                  <Layout><AIAssistant /></Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/login"
              element={
                <PublicRoute>
                  <Login />
                </PublicRoute>
              }
            />
            <Route
              path="/signup"
              element={
                <PublicRoute>
                  <Signup />
                </PublicRoute>
              }
            />
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/auth/google/callback" element={<GoogleCallback />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
