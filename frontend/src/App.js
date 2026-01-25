import React, { useState, useEffect } from 'react';
import client from './api/client';
import { CircleProvider, useCircle } from './contexts/CircleContext';
import CircleSelector from './components/CircleSelector';
import CircleManagement from './components/CircleManagement';
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
  const { circles, setCircles, currentCircle } = useCircle();

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
  }, []);

  const fetchUserData = async () => {
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
  };

  const handleNavClick = (view) => {
    setCurrentView(view);
    setMenuOpen(false);
  };

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
      // Fetch unread matches after login
      if (response.data.circles?.length > 0) {
        fetchUnreadMatches();
      }
    } catch (error) {
      console.error('Login failed:', error);
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
        setCircles(response.data.circles || []);
        setIsLoggedIn(true);
        setDisplayName('');
        // Show welcome screen for new users
        setShowWelcome(true);
      }
    } catch (error) {
      console.error('Registration failed:', error);
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
    return (
      <div className="App">
        <h1>Movie Matcher</h1>
        {inviteCode && (
          <p className="invite-banner">
            You've been invited to join a circle! Create an account to get started.
          </p>
        )}
        {error && <p className="error">{error}</p>}
        {success && <p className="success">{success}</p>}
        <form onSubmit={isRegistering ? handleRegister : handleLogin}>
          {isRegistering && (
            <input
              type="text"
              placeholder="Your name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              autoComplete="name"
            />
          )}
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit">
            {isRegistering ? (inviteCode ? 'Join Circle' : 'Register') : 'Login'}
          </button>
        </form>
        <p className="auth-toggle">
          {isRegistering ? (
            <>Already have an account? <button type="button" className="link-button" onClick={toggleAuthMode}>Login</button></>
          ) : (
            <>Don't have an account? <button type="button" className="link-button" onClick={toggleAuthMode}>Register</button></>
          )}
        </p>
      </div>
    );
  }

  return (
    <div className="App">
      {showWelcome && (
        <Welcome onComplete={() => setShowWelcome(false)} />
      )}
      {showingUnreadMatch && (
        <MatchBanner
          match={showingUnreadMatch}
          onDismiss={handleDismissUnreadMatch}
          autoHide={false}
        />
      )}
      <header className="app-header">
        <h1>Movie Matcher</h1>
        {currentCircle && <CircleSelector />}
        <button className="hamburger" onClick={() => setMenuOpen(!menuOpen)}>
          <span className={menuOpen ? 'open' : ''}></span>
          <span className={menuOpen ? 'open' : ''}></span>
          <span className={menuOpen ? 'open' : ''}></span>
        </button>
      </header>
      <nav className={menuOpen ? 'open' : ''}>
        <button className={currentView === 'swiper' ? 'active' : ''} onClick={() => handleNavClick('swiper')}>Review Movies</button>
        <button className={currentView === 'matches' ? 'active' : ''} onClick={() => handleNavClick('matches')}>View Matches</button>
        <button className={currentView === 'add' ? 'active' : ''} onClick={() => handleNavClick('add')}>Add Movie</button>
        <button className={currentView === 'all' ? 'active' : ''} onClick={() => handleNavClick('all')}>All Movies</button>
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
        <CircleManagement user={user} />
      ) : !currentCircle && circles.length === 0 ? (
        <div className="no-circle">
          <h2>Welcome to Movie Matcher!</h2>
          <p>You're not in any circles yet. Create or join a circle to get started.</p>
          <button onClick={() => handleNavClick('circles')}>Settings</button>
        </div>
      ) : !currentCircle ? (
        <div className="loading">Loading circles...</div>
      ) : (
        <>
          {currentView === 'swiper' && <MovieSwiper />}
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
