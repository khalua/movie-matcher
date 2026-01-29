import React, { useState, useEffect, useRef } from 'react';
import client from './api/client';
import { useCircle } from './contexts/CircleContext';
import './AllMovies.css';

const AllMovies = () => {
  const { currentCircle } = useCircle();
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Movie management state (for circle admins)
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [editingMovie, setEditingMovie] = useState(null);
  const [replacingMovie, setReplacingMovie] = useState(null);
  const [omdbSearch, setOmdbSearch] = useState('');
  const [omdbResults, setOmdbResults] = useState([]);
  const [searchingOmdb, setSearchingOmdb] = useState(false);
  const [message, setMessage] = useState(null);
  const managementPanelRef = useRef(null);

  const isCircleAdmin = currentCircle?.role === 'admin';

  // Debug logging
  console.log('AllMovies - currentCircle:', currentCircle);
  console.log('AllMovies - isCircleAdmin:', isCircleAdmin);
  console.log('AllMovies - selectedMovie:', selectedMovie);

  useEffect(() => {
    fetchAllMovies();
  }, []);

 const fetchAllMovies = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await client.get('/api/movies/all');

      // Sort the movies by title alphabetically
      const sortedMovies = response.data.sort((a, b) => {
        return a.title.localeCompare(b.title);
      });

      setMovies(sortedMovies);
    } catch (error) {
      console.error('Error fetching all movies:', error);
      setError('Failed to fetch movies. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleMovieClick = (movie, e) => {
    e.stopPropagation(); // Prevent event bubbling
    console.log('handleMovieClick called with movie:', movie.title);
    console.log('Current selectedMovie:', selectedMovie?.title);
    console.log('isCircleAdmin at click time:', isCircleAdmin);
    if (!isCircleAdmin) {
      console.log('Returning early - not circle admin');
      return;
    }
    if (selectedMovie?.id === movie.id) {
      console.log('Deselecting movie');
      setSelectedMovie(null);
      setEditingMovie(null);
      setReplacingMovie(null);
      return;
    }
    console.log('Setting selectedMovie to:', movie.title);
    setSelectedMovie(movie);
    setEditingMovie(null);
    setReplacingMovie(null);
    setMessage(null);
    // Scroll to management panel after a short delay
    setTimeout(() => {
      managementPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
  };

  const handleEditMovie = () => {
    setEditingMovie({ ...selectedMovie });
    setReplacingMovie(null);
  };

  const handleSaveMovie = async () => {
    try {
      const response = await client.put(`/api/movies/manage/${editingMovie.id}`, {
        title: editingMovie.title,
        year: editingMovie.year,
        poster: editingMovie.poster,
        description: editingMovie.description,
        genre: editingMovie.genre,
        rating: editingMovie.rating,
        length: editingMovie.length,
        starring: editingMovie.starring
      });
      setMessage({ type: 'success', text: 'Movie updated successfully' });
      setSelectedMovie(response.data.movie);
      setEditingMovie(null);
      fetchAllMovies();
    } catch (err) {
      console.error('Error updating movie:', err);
      setMessage({ type: 'error', text: err.response?.data?.error || 'Failed to update movie' });
    }
  };

  const handleRemoveMovie = async () => {
    if (!window.confirm(`Remove "${selectedMovie.title}" from this circle? This will clear all swipes.`)) {
      return;
    }

    try {
      const response = await client.delete(`/api/movies/manage/${selectedMovie.id}`);
      setMessage({ type: 'success', text: response.data.message });
      setSelectedMovie(null);
      fetchAllMovies();
    } catch (err) {
      console.error('Error removing movie:', err);
      setMessage({ type: 'error', text: err.response?.data?.error || 'Failed to remove movie' });
    }
  };

  const handleStartReplace = () => {
    setReplacingMovie(selectedMovie);
    setOmdbSearch(selectedMovie.title);
    setOmdbResults([]);
    setEditingMovie(null);
  };

  const searchOmdb = async () => {
    if (!omdbSearch.trim()) return;

    setSearchingOmdb(true);
    try {
      const response = await client.get(`/api/movies/search?query=${encodeURIComponent(omdbSearch)}`);
      setOmdbResults(response.data.results || []);
    } catch (err) {
      console.error('Error searching OMDB:', err);
      setMessage({ type: 'error', text: 'Failed to search OMDB' });
    } finally {
      setSearchingOmdb(false);
    }
  };

  const handleReplaceWithMovie = async (omdbMovie) => {
    if (!window.confirm(`Replace "${replacingMovie.title}" with "${omdbMovie.Title}"? This will clear all swipes on the old movie in this circle.`)) {
      return;
    }

    try {
      const response = await client.post(`/api/movies/manage/${replacingMovie.id}/replace`, omdbMovie);
      setMessage({
        type: 'success',
        text: `Replaced "${response.data.old_movie}" with "${response.data.new_movie.title}". ${response.data.swipes_cleared} swipes cleared.`
      });
      setReplacingMovie(null);
      setOmdbResults([]);
      setSelectedMovie(null);
      fetchAllMovies();
    } catch (err) {
      console.error('Error replacing movie:', err);
      setMessage({ type: 'error', text: err.response?.data?.error || 'Failed to replace movie' });
    }
  };

  if (loading) {
    return <div className="loading">Loading movies...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="all-movies-container">
      <h2>All Movies {isCircleAdmin ? '(Admin Mode)' : '(View Only)'}</h2>
      {isCircleAdmin && <p className="admin-hint">Click a movie to edit or replace it</p>}

      {message && (
        <p className={`movie-message ${message.type}`}>{message.text}</p>
      )}

      <table className="movies-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Year</th>
            <th>Genre</th>
            <th>Rating</th>
            <th>Added By</th>
            <th>Not Swiped By</th>
          </tr>
        </thead>
        <tbody>
          {movies.map(movie => (
            <tr
              key={movie.id}
              onClick={(e) => handleMovieClick(movie, e)}
              className={`${isCircleAdmin ? 'clickable' : ''} ${selectedMovie?.id === movie.id ? 'selected' : ''}`}
            >
              <td>{movie.title}</td>
              <td>{movie.year}</td>
              <td>{movie.genre}</td>
              <td>{movie.rating}</td>
              <td>{movie.added_by ? movie.added_by.display_name : 'Unknown'}</td>
              <td>
                {movie.unseen_by.length > 0 ? (
                  <ul className="unseen-users-list">
                    {movie.unseen_by.map(user => (
                      <li key={user.id}>{user.display_name}</li>
                    ))}
                  </ul>
                ) : (
                  "Swiped by all"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {selectedMovie && !editingMovie && !replacingMovie && isCircleAdmin && (
        <div className="movie-management-panel" ref={managementPanelRef}>
          <h3>Manage: {selectedMovie.title} ({selectedMovie.year})</h3>
          <p className="movie-description">{selectedMovie.description}</p>
          <div className="movie-actions">
            <button className="action-btn" onClick={handleEditMovie}>Edit</button>
            <button className="action-btn secondary" onClick={handleStartReplace}>Replace</button>
            <button className="action-btn danger" onClick={handleRemoveMovie}>Remove from Circle</button>
            <button className="action-btn secondary" onClick={() => setSelectedMovie(null)}>Cancel</button>
          </div>
        </div>
      )}

      {editingMovie && isCircleAdmin && (
        <div className="movie-management-panel">
          <h3>Edit Movie</h3>
          <div className="edit-form">
            <label>
              Title
              <input
                type="text"
                value={editingMovie.title}
                onChange={(e) => setEditingMovie({ ...editingMovie, title: e.target.value })}
              />
            </label>
            <label>
              Year
              <input
                type="number"
                value={editingMovie.year}
                onChange={(e) => setEditingMovie({ ...editingMovie, year: e.target.value })}
              />
            </label>
            <label>
              Poster URL
              <input
                type="text"
                value={editingMovie.poster}
                onChange={(e) => setEditingMovie({ ...editingMovie, poster: e.target.value })}
              />
            </label>
            <label>
              Genre
              <input
                type="text"
                value={editingMovie.genre}
                onChange={(e) => setEditingMovie({ ...editingMovie, genre: e.target.value })}
              />
            </label>
            <label>
              Rating
              <input
                type="text"
                value={editingMovie.rating}
                onChange={(e) => setEditingMovie({ ...editingMovie, rating: e.target.value })}
              />
            </label>
            <label>
              Length
              <input
                type="text"
                value={editingMovie.length}
                onChange={(e) => setEditingMovie({ ...editingMovie, length: e.target.value })}
              />
            </label>
            <label>
              Starring
              <input
                type="text"
                value={editingMovie.starring}
                onChange={(e) => setEditingMovie({ ...editingMovie, starring: e.target.value })}
              />
            </label>
            <label>
              Description
              <textarea
                value={editingMovie.description}
                onChange={(e) => setEditingMovie({ ...editingMovie, description: e.target.value })}
                rows={4}
              />
            </label>
            <div className="movie-actions">
              <button className="action-btn" onClick={handleSaveMovie}>Save</button>
              <button className="action-btn secondary" onClick={() => setEditingMovie(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {replacingMovie && isCircleAdmin && (
        <div className="movie-management-panel">
          <h3>Replace "{replacingMovie.title}"</h3>
          <p className="admin-hint">Search OMDB to find the correct movie</p>
          <div className="search-row">
            <input
              type="text"
              value={omdbSearch}
              onChange={(e) => setOmdbSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && searchOmdb()}
              placeholder="Search OMDB..."
              className="search-input"
            />
            <button
              className="action-btn"
              onClick={searchOmdb}
              disabled={searchingOmdb}
            >
              {searchingOmdb ? 'Searching...' : 'Search'}
            </button>
            <button className="action-btn secondary" onClick={() => setReplacingMovie(null)}>Cancel</button>
          </div>

          {omdbResults.length > 0 && (
            <div className="omdb-results">
              {omdbResults.map((movie, index) => (
                <div key={index} className="omdb-result-card">
                  <img
                    src={movie.Poster}
                    alt={movie.Title}
                    className="movie-poster-thumb"
                    onError={(e) => { e.target.style.display = 'none'; }}
                  />
                  <div className="omdb-result-info">
                    <h5>{movie.Title} ({movie.Year})</h5>
                    <p className="movie-meta">{movie.Genre} | {movie.Runtime} | Rating: {movie.imdbRating}</p>
                    <p className="movie-description">{movie.Plot}</p>
                  </div>
                  <button
                    className="action-btn"
                    onClick={() => handleReplaceWithMovie(movie)}
                  >
                    Use This
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AllMovies;