import React, { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { API_BASE_URL } from '../../config';
import './Auth.css';

const GoogleCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Guard against double-execution: the OAuth code is single-use, so we must
    // never call the backend callback endpoint more than once per page load.
    if (hasProcessed.current) return;
    hasProcessed.current = true;

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

