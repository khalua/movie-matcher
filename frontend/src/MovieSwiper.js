import React, { useState, useEffect } from 'react';
import client from './api/client';
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
  const [imageError, setImageError] = useState(false);
  const [streamingServices, setStreamingServices] = useState([]);
  const [swipedElsewhere, setSwipedElsewhere] = useState([]);


  useEffect(() => {
    fetchMovie();
    fetchDebugInfo();
    fetchUserInfo();
  }, []);

  const fetchStreamingAvailability = async (movieId) => {
    try {
      const response = await client.get(`/api/movies/${movieId}/streaming`);
      setStreamingServices(response.data.streaming || []);
    } catch (error) {
      console.error('Error fetching streaming availability:', error);
      setStreamingServices([]);
    }
  };

  const fetchMovie = async () => {
    setLoading(true);
    setError(null);
    setAllDone(false);
    setImageError(false);
    setStreamingServices([]);
    setSwipedElsewhere([]);
    try {
      console.log('Fetching random movie...');
      const response = await client.get('/api/movies/random');
      console.log('Received movie:', response.data);
      setCurrentMovie(response.data);
      // Check if swiped in other circles
      if (response.data.swiped_in_other_circles && response.data.swiped_in_other_circles.length > 0) {
        setSwipedElsewhere(response.data.swiped_in_other_circles);
      }
      // Fetch streaming availability for this movie
      fetchStreamingAvailability(response.data.id);
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
      const response = await client.get('/api/debug/movie-counts');
      setDebugInfo(response.data);
    } catch (error) {
      console.error('Error fetching debug info:', error);
    }
  };

  const fetchUserInfo = async () => {
    try {
      const response = await client.get('/api/user/info');
      setUsername(response.data.username);
    } catch (error) {
      console.error('Error fetching user info:', error);
    }
  };

  const fetchMovieHistory = async () => {
    try {
      const response = await client.get('/api/user/movie-history');
      setMovieHistory(response.data);
    } catch (error) {
      console.error('Error fetching movie history:', error);
    }
  };

  const handleCloseHistory = () => {
    setShowHistory(false);
  };

  const handleSwipe = async (liked) => {
    if (currentMovie) {
      try {
        if (liked) {
          await client.post('/api/movies/like',
            { movieId: currentMovie.id }
          );
          console.log('Movie liked!');
        } else {
          await client.post('/api/movies/dislike',
            { movieId: currentMovie.id }
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
      {debugInfo && (
        <div className="remaining-badge">
          <p>{debugInfo.unseen_movies} movies left</p>
        </div>
      )}
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
            <h2>All Done!</h2>
            <p>You've reviewed all available movies. Check back later or add some new ones!</p>
            <button className="refresh-button" onClick={fetchMovie}>Refresh</button>
          </div>
        ) : currentMovie ? (
          <div className="movie-card">
            {!imageError ? (
              <img
                src={currentMovie.poster}
                alt={currentMovie.title}
                onError={() => setImageError(true)}
              />
            ) : (
              <div className="poster-fallback">
                <div className="poster-placeholder">
                  <svg width="100" height="100" viewBox="0 0 100 100" fill="none">
                    <rect width="100" height="100" fill="#333"/>
                    <path d="M30 40 L50 60 L70 40" stroke="#666" strokeWidth="3" fill="none"/>
                    <circle cx="35" cy="30" r="5" fill="#666"/>
                    <circle cx="65" cy="30" r="5" fill="#666"/>
                  </svg>
                  <p>Poster Unavailable</p>
                </div>
              </div>
            )}
            <div className="movie-info">
              <h2>{currentMovie.title}</h2>
              <p>{currentMovie.year}</p>
              {swipedElsewhere.length > 0 && (
                <div className="swiped-elsewhere-badge">
                  <span className="swiped-label">Already swiped in:</span>
                  {swipedElsewhere.map((swipe, index) => (
                    <span key={index} className={`circle-badge ${swipe.action}`}>
                      {swipe.circle_name} ({swipe.action === 'like' ? '👍' : '👎'})
                    </span>
                  ))}
                </div>
              )}
              {streamingServices.length > 0 && (
                <div className="streaming-services">
                  <span className="streaming-label">Streaming on:</span>
                  {streamingServices.map((service, index) => (
                    <span key={index} className="streaming-badge">{service.name}</span>
                  ))}
                </div>
              )}
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
            <button className="dislike-button" onClick={() => handleSwipe(false)}>Nah, pass</button>
            <button className="like-button" onClick={() => handleSwipe(true)}>Want to watch</button>
          </div>
        )}
      </div>

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