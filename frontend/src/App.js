import React, { useState, useEffect, useCallback } from 'react';
import client from './api/client';
import { CircleProvider, useCircle } from './contexts/CircleContext';
import CircleSelector from './components/CircleSelector';
import CircleManagement from './components/CircleManagement';
import CreateCircleFlow from './components/CreateCircleFlow';
import MatchBanner from './components/MatchBanner';
import Welcome from './components/Welcome';
import MovieSwiper from './MovieSwiper';
import Matches from './Matches';
import AddMovie from './AddMovie';
import AllMovies from './AllMovies';
import Admin from './Admin';
import './App.css';

function AppContent() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [currentView, setCurrentView] = useState('swiper');
  const [menuOpen, setMenuOpen] = useState(false);
  const [user, setUser] = useState(null);
  const [isRegistering, setIsRegistering] = useState(false);
  const [inviteCode, setInviteCode] = useState(null);
  const [unreadMatches, setUnreadMatches] = useState([]);
  const [showingUnreadMatch, setShowingUnreadMatch] = useState(null);
  const [showWelcome, setShowWelcome] = useState(false);
  const [shakeForm, setShakeForm] = useState(false);
  const [unreadCommentsCount, setUnreadCommentsCount] = useState(0);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotPasswordEmail, setForgotPasswordEmail] = useState('');
  const [forgotPasswordSent, setForgotPasswordSent] = useState(false);
  const [showCreateCircleFlow, setShowCreateCircleFlow] = useState(false);
  const { circles, setCircles, currentCircle } = useCircle();

  const fetchUserData = useCallback(async () => {
    try {
      const [circlesRes, profileRes] = await Promise.all([
        client.get('/api/circles'),
        client.get('/api/auth/profile')
      ]);
      setCircles(circlesRes.data);
      setUser(profileRes.data);
      setIsLoggedIn(true);
    } catch (error) {
      console.error('Error fetching user data:', error);
      localStorage.removeItem('token');
      localStorage.removeItem('currentCircleId');
    }
  }, [setCircles]);

  useEffect(() => {
    // Check for invite code in URL
    const path = window.location.pathname;
    const inviteMatch = path.match(/^\/invite\/(.+)$/);
    if (inviteMatch) {
      setInviteCode(inviteMatch[1]);
      setIsRegistering(true);
      // Clean up URL without reloading
      window.history.replaceState({}, '', '/');
    }

    // Check if already logged in
    const token = localStorage.getItem('token');
    if (token) {
      fetchUserData();
    }
  }, [fetchUserData]);

  const handleNavClick = async (view) => {
    setCurrentView(view);
    setMenuOpen(false);
    // Mark comments as read when viewing matches
    if (view === 'matches' && unreadCommentsCount > 0) {
      try {
        await client.post('/api/movies/comments/mark-read');
        setUnreadCommentsCount(0);
      } catch (error) {
        console.error('Error marking comments as read:', error);
      }
    }
  };

  // Track page views in Google Analytics
  useEffect(() => {
    if (window.gtag && isLoggedIn) {
      window.gtag('event', 'page_view', {
        page_title: currentView,
        page_location: window.location.origin + '/' + currentView,
        page_path: '/' + currentView
      });
    }
  }, [currentView, isLoggedIn]);

  // Fetch unread comments count when circle changes
  useEffect(() => {
    if (isLoggedIn && currentCircle) {
      fetchUnreadCommentsCount();
    }
  }, [currentCircle?.id, isLoggedIn]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      const response = await client.post('/api/auth/login', { email, password });
      localStorage.setItem('token', response.data.access_token);
      // Set default circle immediately so API calls have context
      if (response.data.circles?.length > 0) {
        localStorage.setItem('currentCircleId', response.data.circles[0].id);
      }
      setUser(response.data.user);
      setCircles(response.data.circles);
      setIsLoggedIn(true);
      // Show welcome screen if user hasn't seen it
      if (!localStorage.getItem('hasSeenWelcome')) {
        setShowWelcome(true);
      }
      // Fetch unread matches and comments after login
      if (response.data.circles?.length > 0) {
        fetchUnreadMatches();
        fetchUnreadCommentsCount();
      }
    } catch (error) {
      console.error('Login failed:', error);
      // Trigger shake animation
      setShakeForm(true);
      setTimeout(() => setShakeForm(false), 500);

      if (error.response) {
        setError(`Login failed: ${error.response.data.error || error.response.statusText}`);
      } else if (error.request) {
        setError('Login failed: No response from server. Please try again.');
      } else {
        setError(`Login failed: ${error.message}`);
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('currentCircleId');
    setIsLoggedIn(false);
    setCircles([]);
    setCurrentView('swiper');
    setUser(null);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    try {
      let response;
      if (inviteCode) {
        // Register via invitation code
        response = await client.post('/api/auth/invitations/redeem', {
          code: inviteCode,
          email,
          password,
          display_name: displayName || undefined
        });
        localStorage.setItem('token', response.data.access_token);
        setUser(response.data.user);
        setCircles(response.data.circle ? [response.data.circle] : []);
        setIsLoggedIn(true);
        setInviteCode(null);
        setDisplayName('');
        // Show welcome screen for new users
        setShowWelcome(true);
      } else {
        // Regular registration
        response = await client.post('/api/auth/register', {
          email,
          password,
          display_name: displayName || undefined
        });
        localStorage.setItem('token', response.data.access_token);
        setUser(response.data.user);
        const userCircles = response.data.circles || [];
        setCircles(userCircles);
        setIsLoggedIn(true);
        setDisplayName('');
        // Show create circle flow if user has no circles
        if (userCircles.length === 0) {
          setShowCreateCircleFlow(true);
        } else {
          // Show welcome screen for users who already have circles
          setShowWelcome(true);
        }
      }
    } catch (error) {
      console.error('Registration failed:', error);
      // Trigger shake animation
      setShakeForm(true);
      setTimeout(() => setShakeForm(false), 500);

      if (error.response) {
        setError(`Registration failed: ${error.response.data.error || error.response.statusText}`);
      } else if (error.request) {
        setError('Registration failed: No response from server. Please try again.');
      } else {
        setError(`Registration failed: ${error.message}`);
      }
    }
  };

  const toggleAuthMode = () => {
    setIsRegistering(!isRegistering);
    setError(null);
    setSuccess(null);
    setShowForgotPassword(false);
    setForgotPasswordSent(false);
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      await client.post('/api/auth/forgot-password', { email: forgotPasswordEmail });
      setForgotPasswordSent(true);
    } catch (error) {
      // Show success even on error to prevent email enumeration
      setForgotPasswordSent(true);
    }
  };

  const backToLogin = () => {
    setShowForgotPassword(false);
    setForgotPasswordSent(false);
    setForgotPasswordEmail('');
    setError(null);
  };

  const handleTokenUpdate = (newToken, updatedUser) => {
    localStorage.setItem('token', newToken);
    setUser(updatedUser);
  };

  const fetchUnreadMatches = async () => {
    try {
      const response = await client.get('/api/movies/matches/unread');
      const matches = response.data || [];
      if (matches.length > 0) {
        setUnreadMatches(matches);
        setShowingUnreadMatch(matches[0]);
      }
    } catch (error) {
      console.error('Error fetching unread matches:', error);
    }
  };

  const fetchUnreadCommentsCount = async () => {
    try {
      const response = await client.get('/api/movies/comments/unread-count');
      setUnreadCommentsCount(response.data.unread_count || 0);
    } catch (error) {
      console.error('Error fetching unread comments count:', error);
    }
  };

  const handleDismissUnreadMatch = async () => {
    if (showingUnreadMatch) {
      // Mark this match as seen
      try {
        await client.post('/api/movies/matches/mark-seen', {
          last_match_id: showingUnreadMatch.id
        });
      } catch (error) {
        console.error('Error marking match as seen:', error);
      }

      // Show next unread match or clear
      const currentIndex = unreadMatches.findIndex(m => m.id === showingUnreadMatch.id);
      if (currentIndex < unreadMatches.length - 1) {
        setShowingUnreadMatch(unreadMatches[currentIndex + 1]);
      } else {
        setShowingUnreadMatch(null);
        setUnreadMatches([]);
      }
    }
  };

  if (!isLoggedIn) {
    // Forgot Password View
    if (showForgotPassword) {
      return (
        <div className="login-page">
          <div className="login-container">
            <div className="login-brand">
              <div className="login-brand-header">
                <h1>Movie<br/>Matcher</h1>
                <img src="/mm-logo.png" alt="Movie Matcher" className="login-logo" />
              </div>
              <p className="tagline">Find films you all love</p>
            </div>

            <div className="login-form-section">
              {forgotPasswordSent ? (
                <>
                  <p className="success">
                    If an account exists with that email, we've sent password reset instructions.
                  </p>
                  <p className="auth-toggle">
                    <button type="button" className="link-button" onClick={backToLogin}>
                      Back to sign in
                    </button>
                  </p>
                </>
              ) : (
                <>
                  <h2 style={{ color: '#fff', marginBottom: '8px', fontSize: '20px' }}>Reset Password</h2>
                  <p style={{ color: 'rgba(255,255,255,0.6)', marginBottom: '24px', fontSize: '14px' }}>
                    Enter your email and we'll send you a link to reset your password.
                  </p>
                  {error && <p className="error">{error}</p>}
                  <form className="login-form" onSubmit={handleForgotPassword}>
                    <div className="input-group">
                      <label htmlFor="forgotEmail">Email</label>
                      <input
                        id="forgotEmail"
                        type="email"
                        placeholder="you@example.com"
                        value={forgotPasswordEmail}
                        onChange={(e) => setForgotPasswordEmail(e.target.value)}
                        required
                      />
                    </div>
                    <button type="submit" className="submit-btn">Send Reset Link</button>
                  </form>
                  <p className="auth-toggle">
                    <button type="button" className="link-button" onClick={backToLogin}>
                      Back to sign in
                    </button>
                  </p>
                </>
              )}
            </div>
          </div>
        </div>
      );
    }

    // Regular Login/Register View
    return (
      <div className="login-page">
        <div className="login-container">
          <div className="login-brand">
            <div className="login-brand-header">
              <h1>Movie<br/>Matcher</h1>
              <img src="/mm-logo.png" alt="Movie Matcher" className="login-logo" />
            </div>
            <p className="tagline">Find films you all love</p>
          </div>

          <div className="login-form-section">
            {inviteCode && (
              <p className="invite-banner">
                You've been invited to join a circle!
              </p>
            )}
            {error && <p className="error">{error}</p>}
            {success && <p className="success">{success}</p>}

            <form className={`login-form${shakeForm ? ' shake' : ''}`} onSubmit={isRegistering ? handleRegister : handleLogin}>
              {isRegistering && (
                <div className="input-group">
                  <label htmlFor="displayName">Name</label>
                  <input
                    id="displayName"
                    type="text"
                    placeholder="What should we call you?"
                    value={displayName}
                    onChange={(e) => {
                      setDisplayName(e.target.value);
                      setError(null);
                    }}
                    autoComplete="name"
                  />
                </div>
              )}
              <div className="input-group">
                <label htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setError(null);
                  }}
                  required
                />
              </div>
              <div className="input-group">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setError(null);
                  }}
                  required
                />
              </div>
              {!isRegistering && (
                <p className="forgot-password-link">
                  <button type="button" className="link-button" onClick={() => setShowForgotPassword(true)}>
                    Forgot password?
                  </button>
                </p>
              )}
              <button type="submit" className="submit-btn">
                {isRegistering ? (inviteCode ? 'Join Circle' : 'Create Account') : 'Sign In'}
              </button>
            </form>

            <p className="auth-toggle">
              {isRegistering ? (
                <>Have an account? <button type="button" className="link-button" onClick={toggleAuthMode}>Sign in</button></>
              ) : (
                <>New here? <button type="button" className="link-button" onClick={toggleAuthMode}>Create account</button></>
              )}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      {showWelcome && (
        <Welcome onComplete={() => setShowWelcome(false)} circle={currentCircle} />
      )}
      {showingUnreadMatch && (
        <MatchBanner
          match={showingUnreadMatch}
          onDismiss={handleDismissUnreadMatch}
          autoHide={false}
        />
      )}
      <header className="app-header">
        <div className="header-brand" onClick={() => handleNavClick('swiper')}>
          <img src="/mm-logo.png" alt="Movie Matcher" className="header-logo" />
          <h1 className="header-name">Movie Matcher</h1>
        </div>
        {currentCircle && <CircleSelector />}
        <button className="hamburger" onClick={() => setMenuOpen(!menuOpen)}>
          <span className={menuOpen ? 'open' : ''}></span>
          <span className={menuOpen ? 'open' : ''}></span>
          <span className={menuOpen ? 'open' : ''}></span>
        </button>
      </header>
      <nav className={menuOpen ? 'open' : ''}>
        <button className={currentView === 'swiper' ? 'active' : ''} onClick={() => handleNavClick('swiper')}>Swipe Movies</button>
        <button className={currentView === 'matches' ? 'active' : ''} onClick={() => handleNavClick('matches')}>
          View Matches
          {unreadCommentsCount > 0 && <span className="unread-badge">{unreadCommentsCount}</span>}
        </button>
        <button className={currentView === 'add' ? 'active' : ''} onClick={() => handleNavClick('add')}>Add Movies</button>
        {(currentCircle?.role === 'admin' || user?.is_site_admin) && (
          <button className={currentView === 'all' ? 'active' : ''} onClick={() => handleNavClick('all')}>All Movies</button>
        )}
        <button className={currentView === 'circles' ? 'active' : ''} onClick={() => handleNavClick('circles')}>Settings</button>
        <button onClick={() => { setShowWelcome(true); setMenuOpen(false); }}>How it works</button>
        {user?.is_site_admin && (
          <button className={currentView === 'admin' ? 'active' : ''} onClick={() => handleNavClick('admin')}>Admin</button>
        )}
        <button onClick={() => { handleLogout(); setMenuOpen(false); }}>Logout{user?.display_name ? ` (${user.display_name})` : ''}</button>
      </nav>
      {menuOpen && <div className="menu-overlay" onClick={() => setMenuOpen(false)}></div>}

      {currentView === 'admin' && user?.is_site_admin ? (
        <Admin />
      ) : currentView === 'circles' ? (
        <CircleManagement user={user} onTokenUpdate={handleTokenUpdate} />
      ) : showCreateCircleFlow ? (
        <CreateCircleFlow onComplete={() => setShowCreateCircleFlow(false)} />
      ) : !currentCircle ? (
        <div className="loading">Loading circles...</div>
      ) : (
        <>
          {currentView === 'swiper' && <MovieSwiper user={user} />}
          {currentView === 'matches' && <Matches />}
          {currentView === 'add' && <AddMovie user={user} />}
          {currentView === 'all' && <AllMovies />}
        </>
      )}
    </div>
  );
}

function App() {
  return (
    <CircleProvider>
      <AppContent />
    </CircleProvider>
  );
}

export default App;
