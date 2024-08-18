import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Matches.css';

const Matches = () => {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';

  useEffect(() => {
    fetchMatches();
  }, []);

  const fetchMatches = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${apiUrl}/api/movies/matches`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      console.log('Matches response:', response.data); // For debugging
      if (Array.isArray(response.data)) {
        setMatches(response.data);
      } else {
        throw new Error('Received invalid data format');
      }
    } catch (error) {
      console.error('Error fetching matches:', error);
      setError('Failed to fetch matches. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading matches...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (matches.length === 0) {
    return <div className="no-matches">No universal matches found yet. Keep swiping!</div>;
  }

  return (
    <div className="matches-container">
      <h2>Universal Matches</h2>
      <div className="matches-grid">
        {matches.map(movie => (
          <div key={movie.id} className="match-card">
            <img src={movie.poster} alt={movie.title} />
            <h3>{movie.title}</h3>
            <p>Genre: {movie.genre}</p>
            <p>Rating: {movie.rating}</p>
            <p>Liked by all {movie.match_count} users</p>
            <div className="matched-users">
              <h4>Users who liked this movie:</h4>
              <ul>
                {movie.matched_users.map(user => (
                  <li key={user.id}>{user.username}</li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Matches;