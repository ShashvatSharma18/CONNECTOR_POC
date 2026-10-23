import React, { useState } from 'react';
import { User, Lock, Eye, EyeOff, ArrowRight, ShieldCheck, AlertCircle, CheckCircle2 } from 'lucide-react';

interface LoginPageProps {
  onLoginSuccess: (username: string) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedUser = username.trim();
    const trimmedPass = password.trim();

    if (!trimmedUser || !trimmedPass) {
      setError('Please enter both username and password.');
      return;
    }

    setIsLoading(true);

    setTimeout(() => {
      // Validate static credentials: Username: Shashvat (case-insensitive), Password: 0000
      if (trimmedUser.toLowerCase() === 'shashvat' && trimmedPass === '0000') {
        const authData = {
          username: 'Shashvat',
          fullName: 'Shashvat Sharma',
          role: 'AI Assistant Admin',
          loginTime: new Date().toISOString(),
        };

        if (rememberMe) {
          localStorage.setItem('cerebro_auth', JSON.stringify(authData));
        } else {
          sessionStorage.setItem('cerebro_auth', JSON.stringify(authData));
        }

        onLoginSuccess('Shashvat');
      } else {
        setError('Invalid username or password. Please try again.');
        setIsLoading(false);
      }
    }, 400);
  };

  const fillDemoCredentials = () => {
    setUsername('Shashvat');
    setPassword('0000');
    setError(null);
  };

  return (
    <div className="login-page-container">
      {/* Decorative Botanical Watermarks */}
      <div className="login-watermark-top" />
      <div className="login-watermark-bottom" />

      {/* Center Auth Card */}
      <div className="login-card">
        {/* Brand Header */}
        <div className="login-brand-header">
          <div className="login-logo-circle">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
              <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
            </svg>
          </div>
          <h1 className="login-brand-title">Cerebro</h1>
          <p className="login-brand-subtitle">Enterprise AI Workplace Assistant</p>
        </div>

        {/* Welcome Text */}
        <div className="login-welcome-text">
          <h2>Welcome back</h2>
          <p>Please enter your credentials to access your unified workspace.</p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="login-error-banner">
            <AlertCircle size={16} className="error-icon" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field-group">
            <label htmlFor="username">Username</label>
            <div className="login-input-wrapper">
              <User size={17} className="login-input-icon" />
              <input
                id="username"
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                  if (error) setError(null);
                }}
                autoFocus
              />
            </div>
          </div>

          <div className="login-field-group">
            <label htmlFor="password">Password</label>
            <div className="login-input-wrapper">
              <Lock size={17} className="login-input-icon" />
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (error) setError(null);
                }}
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Options: Remember Me & Quick Demo Credentials */}
          <div className="login-options-row">
            <label className="remember-me-label">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
              />
              <span>Remember me</span>
            </label>

            <button
              type="button"
              className="demo-credentials-pill"
              onClick={fillDemoCredentials}
              title="Click to auto-fill Shashvat / 0000"
            >
              Fill Demo Login
            </button>
          </div>

          {/* Sign In Button */}
          <button type="submit" className="login-submit-btn" disabled={isLoading}>
            <span>{isLoading ? 'Signing In...' : 'Sign In to Cerebro'}</span>
            <ArrowRight size={16} />
          </button>
        </form>

        {/* Footer Security Badge */}
        <div className="login-footer-security">
          <ShieldCheck size={14} color="#164E33" />
          <span>Enterprise Secure • 256-bit SSL Encryption</span>
        </div>
      </div>
    </div>
  );
};
