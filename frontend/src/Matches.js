import React, { useState, useEffect } from 'react';
import client from './api/client';
import { useCircle } from './contexts/CircleContext';
import './Matches.css';

const Matches = () => {
  const [users, setUsers] = useState([]);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [streamingData, setStreamingData] = useState({});
  const [expandedMovies, setExpandedMovies] = useState({});

  const [initialLoadDone, setInitialLoadDone] = useState(false);
  const { currentCircle } = useCircle();

  useEffect(() => {
    // Reset state and fetch users when circle changes
    setUsers([]);
    setSelectedUsers([]);
    setMatches([]);
    setStreamingData({});
    setInitialLoadDone(false);
    fetchUsers();
  }, [currentCircle?.id]);

  // Auto-fetch matches when all users are selected on initial load
  useEffect(() => {
    if (initialLoadDone && selectedUsers.length >= 2) {
      fetchMatchesInternal();
    }
  }, [initialLoadDone]);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await client.get('/api/users');
      setUsers(response.data);
      // Select all users by default
      const allUserIds = response.data.map(user => user.id);
      setSelectedUsers(allUserIds);
      setInitialLoadDone(true);
    } catch (error) {
      console.error('Error fetching users:', error);
      setError('Failed to fetch users. Please try again.');
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

  const toggleMovieDetails = (movieId) => {
    setExpandedMovies(prev => ({
      ...prev,
      [movieId]: !prev[movieId]
    }));
  };

  const fetchStreamingForMovie = async (movieId) => {
    try {
      const response = await client.get(`/api/movies/${movieId}/streaming`);
      return response.data.streaming || [];
    } catch (error) {
      console.error(`Error fetching streaming for movie ${movieId}:`, error);
      return [];
    }
  };

  const fetchMatchesInternal = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await client.post('/api/movies/matches', {
        userIds: selectedUsers
      });
      setMatches(response.data);

      // Fetch streaming data for all matched movies
      const streamingPromises = response.data.map(async (movie) => {
        const streaming = await fetchStreamingForMovie(movie.id);
        return { movieId: movie.id, streaming };
      });

      const streamingResults = await Promise.all(streamingPromises);
      const streamingMap = {};
      streamingResults.forEach(({ movieId, streaming }) => {
        streamingMap[movieId] = streaming;
      });
      setStreamingData(streamingMap);
    } catch (error) {
      console.error('Error fetching matches:', error);
      setError('Failed to fetch matches. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const fetchMatches = async () => {
    if (selectedUsers.length < 2) {
      setError('Please select at least two users to compare matches.');
      return;
    }
    fetchMatchesInternal();
  };

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="matches-container">
      <h2>Movie Matches</h2>
      <div className="user-selection">
        {users.map(user => (
          <label key={user.id} className="user-checkbox">
            <input
              type="checkbox"
              checked={selectedUsers.includes(user.id)}
              onChange={() => handleUserSelection(user.id)}
            />
            <span>{user.display_name}</span>
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
            <div key={movie.id} className={`match-card ${expandedMovies[movie.id] ? 'expanded' : ''}`}>
              <img
                src={movie.poster}
                alt={movie.title}
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'flex';
                }}
              />
              <div className="poster-fallback" style={{ display: 'none' }}>
                <div className="poster-placeholder">
                  <p>Poster Unavailable</p>
                </div>
              </div>
              <div className="movie-info">
                <h3>{movie.title}</h3>
                {movie.year && <p className="movie-year">{movie.year}</p>}
                {streamingData[movie.id]?.length > 0 && (
                  <div className="streaming-services">
                    <span className="streaming-label">Streaming on:</span>
                    {streamingData[movie.id].map((service, index) => (
                      <span key={index} className="streaming-badge">
                        {typeof service === 'string' ? service : service.name}
                      </span>
                    ))}
                  </div>
                )}
                <button
                  className="details-toggle"
                  onClick={() => toggleMovieDetails(movie.id)}
                >
                  {expandedMovies[movie.id] ? 'Hide Details' : 'Show Details'}
                </button>
                {expandedMovies[movie.id] && (
                  <div className="movie-details">
                    {movie.description && (
                      <p className="movie-description">{movie.description}</p>
                    )}
                    <div className="movie-meta">
                      {movie.genre && <span className="meta-tag">{movie.genre}</span>}
                      {movie.rating && <span className="meta-tag">{movie.rating}</span>}
                      {movie.length && <span className="meta-tag">{movie.length}</span>}
                    </div>
                    {movie.starring && (
                      <p className="movie-starring">Starring: {movie.starring}</p>
                    )}
                  </div>
                )}
                <div className="matched-users">
                  <h4>Who liked this movie:</h4>
                  <ul>
                    {movie.matched_users.map(user => (
                      <li key={user.id}>{user.display_name}</li>
                    ))}
                  </ul>
                </div>
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