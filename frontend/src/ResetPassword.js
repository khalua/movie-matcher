import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import client from './api/client';
import './ResetPassword.css';

function ResetPassword() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [isValidToken, setIsValidToken] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Verify token on mount
    const verifyToken = async () => {
      try {
        await client.get(`/api/auth/verify-reset-token/${token}`);
        setIsValidToken(true);
      } catch (err) {
        setIsValidToken(false);
        setError(err.response?.data?.error || 'Invalid or expired reset link');
      } finally {
        setIsLoading(false);
      }
    };

    verifyToken();
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    try {
      await client.post('/api/auth/reset-password', {
        token,
        new_password: password
      });
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to reset password');
    }
  };

  if (isLoading) {
    return (
      <div className="reset-password-page">
        <div className="reset-password-container">
          <div className="reset-password-brand">
            <div className="reset-password-brand-header">
              <h1>Movie<br/>Matcher</h1>
              <img src="/mm-logo.png" alt="Movie Matcher" className="reset-password-logo" />
            </div>
          </div>
          <p style={{ color: 'rgba(255,255,255,0.6)' }}>Verifying reset link...</p>
        </div>
      </div>
    );
  }

  if (!isValidToken) {
    return (
      <div className="reset-password-page">
        <div className="reset-password-container">
          <div className="reset-password-brand">
            <div className="reset-password-brand-header">
              <h1>Movie<br/>Matcher</h1>
              <img src="/mm-logo.png" alt="Movie Matcher" className="reset-password-logo" />
            </div>
          </div>
          <div className="reset-password-form-section">
            <p className="error">{error || 'This reset link is invalid or has expired.'}</p>
            <button className="submit-btn" onClick={() => navigate('/')}>
              Back to Sign In
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="reset-password-page">
        <div className="reset-password-container">
          <div className="reset-password-brand">
            <div className="reset-password-brand-header">
              <h1>Movie<br/>Matcher</h1>
              <img src="/mm-logo.png" alt="Movie Matcher" className="reset-password-logo" />
            </div>
          </div>
          <div className="reset-password-form-section">
            <p className="success">Your password has been reset successfully!</p>
            <button className="submit-btn" onClick={() => navigate('/')}>
              Sign In
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="reset-password-page">
      <div className="reset-password-container">
        <div className="reset-password-brand">
          <div className="reset-password-brand-header">
            <h1>Movie<br/>Matcher</h1>
            <img src="/mm-logo.png" alt="Movie Matcher" className="reset-password-logo" />
          </div>
          <p className="tagline">Find films you all love</p>
        </div>

        <div className="reset-password-form-section">
          <h2>Create New Password</h2>
          <p className="subtitle">Enter your new password below.</p>

          {error && <p className="error">{error}</p>}

          <form className="reset-password-form" onSubmit={handleSubmit}>
            <div className="input-group">
              <label htmlFor="password">New Password</label>
              <input
                id="password"
                type="password"
                placeholder="Enter new password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>
            <div className="input-group">
              <label htmlFor="confirmPassword">Confirm Password</label>
              <input
                id="confirmPassword"
                type="password"
                placeholder="Confirm new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>
            <button type="submit" className="submit-btn">Reset Password</button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default ResetPassword;
