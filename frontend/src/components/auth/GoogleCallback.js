import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { API_BASE_URL } from '../../config';
import './Auth.css';

const GoogleCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { checkAuth } = useAuth();

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');

      if (error) {
        navigate('/login', { state: { error: 'Google login cancelled or failed' } });
        return;
      }

      if (!code || !state) {
        navigate('/login', { state: { error: 'Invalid OAuth callback' } });
        return;
      }

      try {
        // Send code to backend
        const response = await fetch(`${API_BASE_URL}/api/auth/google/callback`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({ code, state }),
        });

        const data = await response.json();

        if (data.success) {
          // Refresh auth state
          await checkAuth();
          navigate('/');
        } else {
          navigate('/login', { state: { error: data.message || 'Google login failed' } });
        }
      } catch (error) {
        navigate('/login', { state: { error: 'Network error during Google login' } });
      }
    };

    handleCallback();
  }, [searchParams, navigate, checkAuth]);

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h1>Completing Google Sign In...</h1>
          <p>Please wait while we complete your authentication</p>
        </div>
      </div>
    </div>
  );
};

export default GoogleCallback;

