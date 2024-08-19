import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Matches.css';

const Matches = () => {
  const [users, setUsers] = useState([]);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${apiUrl}/api/users`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUsers(response.data);
    } catch (error) {
      console.error('Error fetching users:', error);
      setError('Failed to fetch users. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleUserSelection = (userId) => {
    setSelectedUsers(prevSelected => {
      if (prevSelected.includes(userId)) {
        return prevSelected.filter(id => id !== userId);
      } else {
        return [...prevSelected, userId];
      }
    });
  };

  const fetchMatches = async () => {
    if (selectedUsers.length < 2) {
      setError('Please select at least two users to compare matches.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${apiUrl}/api/movies/matches`, {
        userIds: selectedUsers
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMatches(response.data);
    } catch (error) {
      console.error('Error fetching matches:', error);
      setError('Failed to fetch matches. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="matches-container">
      <h2>Select Users to Compare Matches</h2>
      <div className="user-selection">
        {users.map(user => (
          <label key={user.id} className="user-checkbox">
            <input
              type="checkbox"
              checked={selectedUsers.includes(user.id)}
              onChange={() => handleUserSelection(user.id)}
            />
            <span>{user.username}</span>
          </label>
        ))}
      </div>
      <button onClick={fetchMatches} disabled={selectedUsers.length < 2}>
        View Matches
      </button>

      {matches.length > 0 ? (
        <div className="matches-grid">
          <h3>Matches for Selected Users</h3>
          {matches.map(movie => (
            <div key={movie.id} className="match-card">
              <img src={movie.poster} alt={movie.title} />
              <h3>{movie.title}</h3>
              <p>Genre: {movie.genre}</p>
              <p>Rating: {movie.rating}</p>
              <div className="matched-users">
                <h4>Who liked this movie:</h4>
                <ul>
                  {movie.matched_users.map(user => (
                    <li key={user.id}>{user.username}</li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="no-matches">No matches found between the selected users.</div>
      )}
    </div>
  );
};

export default Matches;