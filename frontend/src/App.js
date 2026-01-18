import React, { useState, useEffect } from 'react';
import client from './api/client';
import { CircleProvider, useCircle } from './contexts/CircleContext';
import CircleSelector from './components/CircleSelector';
import CircleManagement from './components/CircleManagement';
import MovieSwiper from './MovieSwiper';
import Matches from './Matches';
import AddMovie from './AddMovie';
import AllMovies from './AllMovies';
import './App.css';

function AppContent() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [currentView, setCurrentView] = useState('swiper');
  const [menuOpen, setMenuOpen] = useState(false);
  const [user, setUser] = useState(null);
  const { circles, setCircles, currentCircle } = useCircle();

  useEffect(() => {
    // Check if already logged in
    const token = localStorage.getItem('token');
    if (token) {
      fetchUserData();
    }
  }, []);

  const fetchUserData = async () => {
    try {
      const response = await client.get('/api/circles');
      setCircles(response.data);
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
      setUser(response.data.user);
      setCircles(response.data.circles);
      setIsLoggedIn(true);
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

  if (!isLoggedIn) {
    return (
      <div className="App">
        <h1>Movie Matcher</h1>
        {error && <p className="error">{error}</p>}
        <form onSubmit={handleLogin}>
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
          <button type="submit">Login</button>
        </form>
        <p className="hint">
          Don't have an account? Contact an admin for an invitation code.
        </p>
      </div>
    );
  }

  return (
    <div className="App">
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
        <button className={currentView === 'circles' ? 'active' : ''} onClick={() => handleNavClick('circles')}>Manage Circles</button>
        <button onClick={() => { handleLogout(); setMenuOpen(false); }}>Logout</button>
      </nav>
      {menuOpen && <div className="menu-overlay" onClick={() => setMenuOpen(false)}></div>}

      {!currentCircle && circles.length === 0 ? (
        <div className="no-circle">
          <h2>Welcome to Movie Matcher!</h2>
          <p>You're not in any circles yet. Create or join a circle to get started.</p>
          <button onClick={() => handleNavClick('circles')}>Manage Circles</button>
        </div>
      ) : !currentCircle ? (
        <div className="loading">Loading circles...</div>
      ) : (
        <>
          {currentView === 'swiper' && <MovieSwiper />}
          {currentView === 'matches' && <Matches />}
          {currentView === 'add' && <AddMovie />}
          {currentView === 'all' && <AllMovies />}
          {currentView === 'circles' && <CircleManagement user={user} />}
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
