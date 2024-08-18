import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './MovieSwiper.css';

const MovieSwiper = () => {
  const [currentMovie, setCurrentMovie] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [allDone, setAllDone] = useState(false);
  const [debugInfo, setDebugInfo] = useState(null);
  const [username, setUsername] = useState('');
  const [showHistory, setShowHistory] = useState(false);
  const [movieHistory, setMovieHistory] = useState([]);
  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';


  useEffect(() => {
    fetchMovie();
    fetchDebugInfo();
    fetchUserInfo();
  }, []);

  const fetchMovie = async () => {
    setLoading(true);
    setError(null);
    setAllDone(false);
    try {
      const token = localStorage.getItem('token');
      console.log('Fetching random movie...');
      const response = await axios.get(`${apiUrl}/api/movies/random`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      console.log('Received movie:', response.data);
      setCurrentMovie(response.data);
    } catch (error) {
      console.error('Error fetching movie:', error);
      if (error.response && error.response.status === 404) {
        setAllDone(true);
      } else if (error.response) {
        setError(`Server error: ${error.response.status} - ${error.response.data.message || 'Unknown error'}`);
      } else if (error.request) {
        setError('No response received from server. Please check your connection.');
      } else {
        setError(`Error: ${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchDebugInfo = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${apiUrl}/api/debug/movie-counts`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDebugInfo(response.data);
    } catch (error) {
      console.error('Error fetching debug info:', error);
    }
  };

  const fetchUserInfo = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${apiUrl}/api/user/info`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUsername(response.data.username);
    } catch (error) {
      console.error('Error fetching user info:', error);
    }
  };

  const fetchMovieHistory = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${apiUrl}/api/user/movie-history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMovieHistory(response.data);
    } catch (error) {
      console.error('Error fetching movie history:', error);
    }
  };

  const handleShowHistory = (e) => {
    e.preventDefault();
    fetchMovieHistory();
    setShowHistory(true);
  };

  const handleCloseHistory = () => {
    setShowHistory(false);
  };

  const handleSwipe = async (liked) => {
    if (currentMovie) {
      try {
        const token = localStorage.getItem('token');
        if (liked) {
          await axios.post(`${apiUrl}/api/movies/like`, 
            { movieId: currentMovie.id },
            { headers: { Authorization: `Bearer ${token}` } }
          );
          console.log('Movie liked!');
        } else {
          await axios.post(`${apiUrl}/api/movies/dislike`, 
            { movieId: currentMovie.id },
            { headers: { Authorization: `Bearer ${token}` } }
          );
          console.log('Movie disliked!');
        }
      } catch (error) {
        console.error(`Error ${liked ? 'liking' : 'disliking'} movie:`, error);
      }
    }
    fetchMovie();
    fetchDebugInfo();
  };

  return (
    <div className="movie-swiper">
      <div className="user-info">
        <button className="username-button" onClick={handleShowHistory}>
          {username ? `Logged in as: ${username}` : 'Loading...'}
        </button>
      </div>

      <div className="movie-container">
        {loading ? (
          <div className="loading">Loading movie...</div>
        ) : error ? (
          <div className="error">
            <p>{error}</p>
            <button onClick={fetchMovie}>Try Again</button>
          </div>
        ) : allDone ? (
          <div className="all-done">
            <h2>Done!</h2>
            <p>Check again later for new movies or better yet add a new movie.</p>
            <button className="refresh-button" onClick={fetchMovie}>Refresh</button>
          </div>
        ) : currentMovie ? (
          <div className="movie-card">
            <img src={currentMovie.poster} alt={currentMovie.title} />
            <div className="movie-info">
              <h2>{currentMovie.title}</h2>
              <p>{currentMovie.year}</p>
              <p>{currentMovie.description}</p>
              <p>Genre: {currentMovie.genre}</p>
              <p>Rating: {currentMovie.rating}</p>
              <p>Length: {currentMovie.length}</p>
              <p>Starring: {currentMovie.starring}</p>
            </div>
          </div>
        ) : (
          <div className="no-movies">No movie available at the moment.</div>
        )}

        {currentMovie && (
          <div className="swipe-buttons">
            <button className="dislike-button" onClick={() => handleSwipe(false)}>Nah</button>
            <button className="like-button" onClick={() => handleSwipe(true)}>Want to watch</button>
          </div>
        )}
      </div>

      {debugInfo && (
        <div className="debug-info">
          <p>Remaining Movies: {debugInfo.unseen_movies}</p>
        </div>
      )}

      {showHistory && (
        <div className="modal">
          <div className="modal-content">
            <h2>Movie History for {username}</h2>
            <table>
              <thead>
                <tr>
                  <th>Movie</th>
                  <th>Liked</th>
                </tr>
              </thead>
              <tbody>
                {movieHistory.map((movie, index) => (
                  <tr key={index}>
                    <td>{movie.title}</td>
                    <td>{movie.liked ? 'Yes' : 'No'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button onClick={handleCloseHistory}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default MovieSwiper;