import React, { useState } from 'react';
import axios from 'axios';
import MovieSwiper from './MovieSwiper';
import Matches from './Matches';
import AddMovie from './AddMovie';
import AllMovies from './AllMovies';
import './App.css';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [currentView, setCurrentView] = useState('swiper');
  const [menuOpen, setMenuOpen] = useState(false);
  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';

  const handleNavClick = (view) => {
    setCurrentView(view);
    setMenuOpen(false);
  };


  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const response = await axios.post(`${apiUrl}/api/auth/login`, { username, password });
      if (response.data && response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
        setIsLoggedIn(true);
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (error) {
      console.error('Login failed:', error);
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        setError(`Login failed: ${error.response.data.message || error.response.statusText}`);
      } else if (error.request) {
        // The request was made but no response was received
        setError('Login failed: No response from server. Please try again.');
      } else {
        // Something happened in setting up the request that triggered an Error
        setError(`Login failed: ${error.message}`);
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsLoggedIn(false);
    setCurrentView('swiper');
  };


  if (!isLoggedIn) {
    return (
      <div className="App">
        <h1>Movie Matcher</h1>
        {error && <p className="error">{error}</p>}
        <form onSubmit={handleLogin}>
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button type="submit">Login</button>
        </form>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="app-header">
        <h1>Movie Matcher</h1>
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
        <button onClick={() => { handleLogout(); setMenuOpen(false); }}>Logout</button>
      </nav>
      {menuOpen && <div className="menu-overlay" onClick={() => setMenuOpen(false)}></div>}
      {currentView === 'swiper' && <MovieSwiper />}
      {currentView === 'matches' && <Matches />}
      {currentView === 'add' && <AddMovie />}
      {currentView === 'all' && <AllMovies />}
    </div>
  );
}

export default App;