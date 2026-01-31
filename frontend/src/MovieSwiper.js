import React, { useState, useEffect, useRef, useCallback } from 'react';
import client from './api/client';
import { useCircle } from './contexts/CircleContext';
import MatchBanner from './components/MatchBanner';
import './MovieSwiper.css';

const MovieSwiper = ({ user, onNavigate }) => {
  const { refreshCircles, currentCircle } = useCircle();
  const [currentMovie, setCurrentMovie] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [allDone, setAllDone] = useState(false);
  const [username, setUsername] = useState('');
  const [showHistory, setShowHistory] = useState(false);
  const [movieHistory, setMovieHistory] = useState([]);
  const [imageError, setImageError] = useState(false);
  const [streamingServices, setStreamingServices] = useState([]);
  const [swipedElsewhere, setSwipedElsewhere] = useState([]);
  const [swipeCount, setSwipeCount] = useState(0);
  const sortOrder = localStorage.getItem('movieSortOrder') || 'random';
  const [currentMatch, setCurrentMatch] = useState(null);

  // Swipe gesture state
  const [dragState, setDragState] = useState({ x: 0, y: 0, isDragging: false });
  const [isExiting, setIsExiting] = useState(false);
  const [exitDirection, setExitDirection] = useState(null);
  const [swipeConfirmation, setSwipeConfirmation] = useState(null); // 'like' or 'dislike'
  const cardRef = useRef(null);
  const startPos = useRef({ x: 0, y: 0 });
  const SWIPE_THRESHOLD = 100; // pixels needed to trigger swipe


  useEffect(() => {
    fetchMovie();
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

  const fetchMovie = async (overrideSort = null) => {
    const sort = overrideSort || sortOrder;
    setLoading(true);
    setError(null);
    setAllDone(false);
    setImageError(false);
    setStreamingServices([]);
    setSwipedElsewhere([]);
    try {
      console.log(`Fetching movie (sort=${sort}, swipe_count=${swipeCount})...`);
      const response = await client.get(`/api/movies/random?sort=${sort}&swipe_count=${swipeCount}`);
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

  
  const fetchUserInfo = async () => {
    try {
      const response = await client.get('/api/auth/profile');
      setUsername(response.data.display_name || response.data.email);
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
          const response = await client.post('/api/movies/like',
            { movieId: currentMovie.id }
          );
          console.log('Movie liked!');
          // Check if this created a match
          if (response.data.match) {
            setCurrentMatch(response.data.match);
          }
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
    setSwipeCount(prev => prev + 1);
    fetchMovie();
    refreshCircles();
  };

  const handleDismissMatch = () => {
    setCurrentMatch(null);
  };

  // Show swipe confirmation overlay
  const showSwipeConfirmation = (liked) => {
    setSwipeConfirmation(liked ? 'like' : 'dislike');
    setTimeout(() => {
      setSwipeConfirmation(null);
    }, 800);
  };

  // Touch/Mouse event handlers for swipe gestures
  const handleDragStart = useCallback((clientX, clientY) => {
    if (isExiting) return;
    startPos.current = { x: clientX, y: clientY };
    setDragState({ x: 0, y: 0, isDragging: true });
  }, [isExiting]);

  const handleDragMove = useCallback((clientX, clientY) => {
    if (!dragState.isDragging || isExiting) return;
    const deltaX = clientX - startPos.current.x;
    const deltaY = clientY - startPos.current.y;
    setDragState({ x: deltaX, y: deltaY, isDragging: true });
  }, [dragState.isDragging, isExiting]);

  const handleDragEnd = useCallback(() => {
    if (!dragState.isDragging || isExiting) return;

    const { x } = dragState;

    if (Math.abs(x) > SWIPE_THRESHOLD) {
      // Trigger swipe
      const liked = x > 0;
      setExitDirection(liked ? 'right' : 'left');
      setIsExiting(true);

      // Wait for exit animation, then process
      setTimeout(() => {
        handleSwipe(liked);
        showSwipeConfirmation(liked);
        setDragState({ x: 0, y: 0, isDragging: false });
        setIsExiting(false);
        setExitDirection(null);
      }, 300);
    } else {
      // Snap back
      setDragState({ x: 0, y: 0, isDragging: false });
    }
  }, [dragState, isExiting]);

  // Touch event handlers
  const onTouchStart = (e) => {
    const touch = e.touches[0];
    handleDragStart(touch.clientX, touch.clientY);
  };

  const onTouchMove = (e) => {
    const touch = e.touches[0];
    handleDragMove(touch.clientX, touch.clientY);
  };

  const onTouchEnd = () => {
    handleDragEnd();
  };

  // Mouse event handlers (for desktop testing)
  const onMouseDown = (e) => {
    e.preventDefault();
    handleDragStart(e.clientX, e.clientY);
  };

  const onMouseMove = (e) => {
    if (dragState.isDragging) {
      handleDragMove(e.clientX, e.clientY);
    }
  };

  const onMouseUp = () => {
    handleDragEnd();
  };

  const onMouseLeave = () => {
    if (dragState.isDragging) {
      handleDragEnd();
    }
  };

  // Calculate card transform and opacity for indicators
  const getCardStyle = () => {
    if (isExiting) {
      const exitX = exitDirection === 'right' ? window.innerWidth : -window.innerWidth;
      return {
        transform: `translateX(${exitX}px) rotate(${exitDirection === 'right' ? 30 : -30}deg)`,
        transition: 'transform 0.3s ease-out',
      };
    }

    const { x, y, isDragging } = dragState;
    const rotation = x * 0.1; // Rotate based on drag

    return {
      transform: `translateX(${x}px) translateY(${y * 0.3}px) rotate(${rotation}deg)`,
      transition: isDragging ? 'none' : 'transform 0.3s ease-out',
      cursor: isDragging ? 'grabbing' : 'grab',
    };
  };

  const getLikeOpacity = () => Math.min(Math.max(dragState.x / SWIPE_THRESHOLD, 0), 1);
  const getNopeOpacity = () => Math.min(Math.max(-dragState.x / SWIPE_THRESHOLD, 0), 1);

  return (
    <div className="movie-swiper">
      {/* Swipe confirmation overlay */}
      {swipeConfirmation && (
        <div className={`swipe-confirmation ${swipeConfirmation}`}>
          {swipeConfirmation === 'like' ? '❤️' : '👎'}
        </div>
      )}

      {currentMatch && (
        <MatchBanner
          match={currentMatch}
          onDismiss={handleDismissMatch}
          autoHide={true}
          autoHideDelay={5000}
        />
      )}
      {user?.is_site_admin && currentCircle?.unseen_count !== undefined && (
        <div className="remaining-badge">
          <p>{currentCircle.unseen_count} movies left</p>
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
            {currentCircle?.role === 'admin' ? (
              <>
                <p>There are no movies in the {currentCircle.name} circle yet.</p>
                <p className="admin-hint">Add movie packs or search for specific films to get started.</p>
                <button className="refresh-button" onClick={() => onNavigate?.('add')}>Add Movies</button>
              </>
            ) : (
              <>
                <p>You've reviewed all available movies. Check back later or add some new ones!</p>
                <button className="refresh-button" onClick={() => fetchMovie()}>Refresh</button>
              </>
            )}
          </div>
        ) : currentMovie ? (
          <div
            className={`movie-card ${dragState.isDragging ? 'dragging' : ''}`}
            ref={cardRef}
            style={getCardStyle()}
            onTouchStart={onTouchStart}
            onTouchMove={onTouchMove}
            onTouchEnd={onTouchEnd}
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            onMouseLeave={onMouseLeave}
          >
            {/* Swipe indicators */}
            <div className="swipe-indicator like" style={{ opacity: getLikeOpacity() }}>
              LIKE
            </div>
            <div className="swipe-indicator nope" style={{ opacity: getNopeOpacity() }}>
              NOPE
            </div>

            {!imageError ? (
              <img
                src={currentMovie.poster}
                alt={currentMovie.title}
                onError={() => setImageError(true)}
                draggable="false"
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
                    <span key={index} className="streaming-badge">
                      {typeof service === 'string' ? service : service.name}
                    </span>
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
            <button className="dislike-button" onClick={() => { handleSwipe(false); showSwipeConfirmation(false); }}>Nah, pass</button>
            <button className="like-button" onClick={() => { handleSwipe(true); showSwipeConfirmation(true); }}>Want to watch</button>
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