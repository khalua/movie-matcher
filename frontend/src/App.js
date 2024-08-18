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
  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';


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
      <h1>Movie Matcher</h1>
      <nav>
        <button onClick={() => setCurrentView('swiper')}>Swipe Movies</button>
        <button onClick={() => setCurrentView('matches')}>View Matches</button>
        <button onClick={() => setCurrentView('add')}>Add Movie</button>
        <button onClick={() => setCurrentView('all')}>All Movies</button>
        <button onClick={handleLogout}>Logout</button>
      </nav>
      {currentView === 'swiper' && <MovieSwiper />}
      {currentView === 'matches' && <Matches />}
      {currentView === 'add' && <AddMovie />}
      {currentView === 'all' && <AllMovies />}
    </div>
  );
}

export default App;