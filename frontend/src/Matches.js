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
  const [selectionChanged, setSelectionChanged] = useState(false);
  const { currentCircle } = useCircle();

  // Seen movies state
  const [viewMode, setViewMode] = useState('matches'); // 'matches' or 'seen'
  const [seenMovies, setSeenMovies] = useState([]);
  const [loadingSeen, setLoadingSeen] = useState(false);

  // Comments state
  const [comments, setComments] = useState({}); // { movieId: [comments] }
  const [showComments, setShowComments] = useState({}); // { movieId: boolean }
  const [newComment, setNewComment] = useState({}); // { movieId: string }
  const [submittingComment, setSubmittingComment] = useState({});

  useEffect(() => {
    // Reset state and fetch users when circle changes
    setUsers([]);
    setSelectedUsers([]);
    setMatches([]);
    setStreamingData({});
    setInitialLoadDone(false);
    setSelectionChanged(false);
    setViewMode('matches');
    setSeenMovies([]);
    setComments({});
    setShowComments({});
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
    setSelectionChanged(true);
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

  // Seen movies functions
  const fetchSeenMovies = async () => {
    setLoadingSeen(true);
    try {
      const response = await client.get('/api/movies/seen');
      setSeenMovies(response.data);

      // Fetch streaming data for seen movies
      const streamingPromises = response.data.map(async (movie) => {
        const streaming = await fetchStreamingForMovie(movie.id);
        return { movieId: movie.id, streaming };
      });

      const streamingResults = await Promise.all(streamingPromises);
      const streamingMap = { ...streamingData };
      streamingResults.forEach(({ movieId, streaming }) => {
        streamingMap[movieId] = streaming;
      });
      setStreamingData(streamingMap);
    } catch (error) {
      console.error('Error fetching seen movies:', error);
    } finally {
      setLoadingSeen(false);
    }
  };

  const handleMarkSeen = async (movieId) => {
    try {
      await client.post(`/api/movies/${movieId}/mark-seen`);
      // Remove from matches list
      setMatches(prev => prev.filter(m => m.id !== movieId));
    } catch (error) {
      console.error('Error marking movie as seen:', error);
      if (error.response?.data?.error) {
        setError(error.response.data.error);
      }
    }
  };

  const handleUndoSeen = async (movieId) => {
    try {
      await client.delete(`/api/movies/${movieId}/mark-seen`);
      // Remove from seen movies list
      setSeenMovies(prev => prev.filter(m => m.id !== movieId));
    } catch (error) {
      console.error('Error undoing seen:', error);
      if (error.response?.data?.error) {
        setError(error.response.data.error);
      }
    }
  };

  const handleViewModeChange = (mode) => {
    setViewMode(mode);
    if (mode === 'seen') {
      fetchSeenMovies();
    }
  };

  // Comments functions
  const fetchComments = async (movieId) => {
    try {
      const response = await client.get(`/api/movies/${movieId}/comments`);
      setComments(prev => ({
        ...prev,
        [movieId]: response.data
      }));
    } catch (error) {
      console.error('Error fetching comments:', error);
    }
  };

  const toggleComments = async (movieId) => {
    const isShowing = !showComments[movieId];
    setShowComments(prev => ({
      ...prev,
      [movieId]: isShowing
    }));
    if (isShowing) {
      if (!comments[movieId]) {
        fetchComments(movieId);
      }
      // Mark comments as read and clear unread count for this movie
      try {
        await client.post('/api/movies/comments/mark-read');
        setMatches(prev => prev.map(m =>
          m.id === movieId ? { ...m, unread_comment_count: 0 } : m
        ));
        setSeenMovies(prev => prev.map(m =>
          m.id === movieId ? { ...m, unread_comment_count: 0 } : m
        ));
      } catch (error) {
        console.error('Error marking comments as read:', error);
      }
    }
  };

  const handleAddComment = async (movieId) => {
    const content = newComment[movieId]?.trim();
    if (!content) return;

    setSubmittingComment(prev => ({ ...prev, [movieId]: true }));
    try {
      const response = await client.post(`/api/movies/${movieId}/comments`, { content });
      setComments(prev => ({
        ...prev,
        [movieId]: [response.data, ...(prev[movieId] || [])]
      }));
      setNewComment(prev => ({ ...prev, [movieId]: '' }));
      // Update comment count in matches and seenMovies
      setMatches(prev => prev.map(m =>
        m.id === movieId ? { ...m, comment_count: (m.comment_count || 0) + 1 } : m
      ));
      setSeenMovies(prev => prev.map(m =>
        m.id === movieId ? { ...m, comment_count: (m.comment_count || 0) + 1 } : m
      ));
    } catch (error) {
      console.error('Error adding comment:', error);
    } finally {
      setSubmittingComment(prev => ({ ...prev, [movieId]: false }));
    }
  };

  const handleDeleteComment = async (movieId, commentId) => {
    try {
      await client.delete(`/api/movies/${movieId}/comments/${commentId}`);
      setComments(prev => ({
        ...prev,
        [movieId]: prev[movieId].filter(c => c.id !== commentId)
      }));
      // Update comment count in matches and seenMovies
      setMatches(prev => prev.map(m =>
        m.id === movieId ? { ...m, comment_count: Math.max(0, (m.comment_count || 1) - 1) } : m
      ));
      setSeenMovies(prev => prev.map(m =>
        m.id === movieId ? { ...m, comment_count: Math.max(0, (m.comment_count || 1) - 1) } : m
      ));
    } catch (error) {
      console.error('Error deleting comment:', error);
    }
  };

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const renderMovieCard = (movie, isSeen = false) => (
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

        {isSeen && movie.seen_info && (
          <div className="seen-info">
            <span className="seen-by">{movie.seen_info.marked_by.display_name}</span>
            <span> marked as seen on {formatDate(movie.seen_info.marked_at)}</span>
          </div>
        )}

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

        {/* Action buttons */}
        {!isSeen ? (
          <button
            className="mark-seen-btn"
            onClick={() => handleMarkSeen(movie.id)}
          >
            We watched this!
          </button>
        ) : (
          <button
            className="undo-seen-btn"
            onClick={() => handleUndoSeen(movie.id)}
          >
            Undo Seen
          </button>
        )}

        {/* Comments section for all movies */}
        <div className="comments-section">
          <button
            className={`comments-toggle ${movie.unread_comment_count > 0 ? 'has-unread' : ''}`}
            onClick={() => toggleComments(movie.id)}
          >
            {showComments[movie.id] ? 'Hide Comments' : `Comments (${movie.comment_count || 0})`}
            {movie.unread_comment_count > 0 && (
              <span className="unread-badge">{movie.unread_comment_count} new</span>
            )}
          </button>

          {showComments[movie.id] && (
            <div className="comments-container">
              <div className="comment-form">
                <textarea
                  value={newComment[movie.id] || ''}
                  onChange={(e) => setNewComment(prev => ({ ...prev, [movie.id]: e.target.value }))}
                  placeholder="Add a comment..."
                  maxLength={1000}
                />
                <button
                  onClick={() => handleAddComment(movie.id)}
                  disabled={submittingComment[movie.id] || !newComment[movie.id]?.trim()}
                >
                  {submittingComment[movie.id] ? 'Posting...' : 'Post'}
                </button>
              </div>

              <div className="comments-list">
                {comments[movie.id]?.length > 0 ? (
                  comments[movie.id].map(comment => (
                    <div key={comment.id} className="comment">
                      <div className="comment-header">
                        <span className="comment-author">{comment.author.display_name}</span>
                        <span className="comment-date">{formatDate(comment.created_at)}</span>
                      </div>
                      <p className="comment-content">{comment.content}</p>
                      {comment.can_delete && (
                        <button
                          className="delete-comment"
                          onClick={() => handleDeleteComment(movie.id, comment.id)}
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="no-comments">No comments yet</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="matches-container">
      <h2>Movie Matches</h2>

      {/* View Mode Tabs */}
      <div className="view-tabs">
        <div
          className={`view-tab ${viewMode === 'matches' ? 'active' : ''}`}
          onClick={() => handleViewModeChange('matches')}
        >
          Matches
        </div>
        <div
          className={`view-tab ${viewMode === 'seen' ? 'active' : ''}`}
          onClick={() => handleViewModeChange('seen')}
        >
          Seen Movies
        </div>
      </div>

      {viewMode === 'matches' ? (
        <>
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
          {selectionChanged && (
            <button onClick={fetchMatches} disabled={selectedUsers.length < 2}>
              View Matches
            </button>
          )}

          {matches.length > 0 ? (
            <div className="matches-grid">
              <h3>Matches for Selected Users</h3>
              {matches.map(movie => renderMovieCard(movie, false))}
            </div>
          ) : (
            <div className="no-matches">No matches found between the selected users.</div>
          )}
        </>
      ) : (
        <>
          {loadingSeen ? (
            <div className="loading">Loading seen movies...</div>
          ) : seenMovies.length > 0 ? (
            <div className="matches-grid">
              <h3>Movies You've Watched</h3>
              {seenMovies.map(movie => renderMovieCard(movie, true))}
            </div>
          ) : (
            <div className="no-matches">No seen movies yet. Mark a match as seen to track watched movies.</div>
          )}
        </>
      )}
    </div>
  );
};

export default Matches;
