import React, { useState, useEffect } from 'react';
import client from './api/client';
import './Admin.css';

function Admin() {
  const [activeTab, setActiveTab] = useState('overview');
  const [analytics, setAnalytics] = useState(null);
  const [circles, setCircles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [seeding, setSeeding] = useState(false);
  const [seedMessage, setSeedMessage] = useState(null);
  const [selectedCircle, setSelectedCircle] = useState(null);
  const [members, setMembers] = useState([]);
  const [loadingMembers, setLoadingMembers] = useState(false);

  // Movie management state
  const [movieSearch, setMovieSearch] = useState('');
  const [movies, setMovies] = useState([]);
  const [loadingMovies, setLoadingMovies] = useState(false);
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [editingMovie, setEditingMovie] = useState(null);
  const [movieMessage, setMovieMessage] = useState(null);
  const [replacingMovie, setReplacingMovie] = useState(null);
  const [omdbSearch, setOmdbSearch] = useState('');
  const [omdbResults, setOmdbResults] = useState([]);
  const [searchingOmdb, setSearchingOmdb] = useState(false);

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      const [analyticsRes, circlesRes] = await Promise.all([
        client.get('/api/admin/analytics'),
        client.get('/api/admin/circles')
      ]);
      setAnalytics(analyticsRes.data);
      setCircles(circlesRes.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching admin data:', err);
      setError('Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  const handleCircleClick = async (circle) => {
    if (selectedCircle?.id === circle.id) {
      setSelectedCircle(null);
      setMembers([]);
      return;
    }

    setSelectedCircle(circle);
    setLoadingMembers(true);

    try {
      const response = await client.get(`/api/admin/circles/${circle.id}/members`);
      console.log('Members response:', response.data);
      setMembers(response.data);
    } catch (err) {
      console.error('Error fetching members:', err.response?.data || err.message);
      setMembers([]);
    } finally {
      setLoadingMembers(false);
    }
  };

  const handleSeedCircles = async () => {
    if (!window.confirm('This will add movies from top_movies.txt to ALL circles. Continue?')) {
      return;
    }

    try {
      setSeeding(true);
      setSeedMessage(null);
      const response = await client.post('/api/admin/seed-circles');
      setSeedMessage(response.data.message);
      fetchAdminData();
    } catch (err) {
      console.error('Error seeding circles:', err);
      setSeedMessage('Failed to seed circles');
    } finally {
      setSeeding(false);
    }
  };

  // Movie management functions
  const searchMovies = async () => {
    if (!movieSearch.trim()) return;

    setLoadingMovies(true);
    setMovieMessage(null);
    try {
      const response = await client.get(`/api/admin/movies?search=${encodeURIComponent(movieSearch)}`);
      setMovies(response.data);
      setSelectedMovie(null);
      setEditingMovie(null);
    } catch (err) {
      console.error('Error searching movies:', err);
      setMovieMessage({ type: 'error', text: 'Failed to search movies' });
    } finally {
      setLoadingMovies(false);
    }
  };

  const handleMovieClick = async (movie) => {
    if (selectedMovie?.id === movie.id) {
      setSelectedMovie(null);
      return;
    }

    try {
      const response = await client.get(`/api/admin/movies/${movie.id}`);
      setSelectedMovie(response.data);
      setEditingMovie(null);
      setReplacingMovie(null);
    } catch (err) {
      console.error('Error fetching movie details:', err);
    }
  };

  const handleEditMovie = () => {
    setEditingMovie({ ...selectedMovie });
    setReplacingMovie(null);
  };

  const handleSaveMovie = async () => {
    try {
      const response = await client.put(`/api/admin/movies/${editingMovie.id}`, {
        title: editingMovie.title,
        year: editingMovie.year,
        poster: editingMovie.poster,
        description: editingMovie.description,
        genre: editingMovie.genre,
        rating: editingMovie.rating,
        length: editingMovie.length,
        starring: editingMovie.starring
      });
      setMovieMessage({ type: 'success', text: 'Movie updated successfully' });
      setSelectedMovie(response.data.movie);
      setEditingMovie(null);
      // Refresh the search results
      searchMovies();
    } catch (err) {
      console.error('Error updating movie:', err);
      setMovieMessage({ type: 'error', text: err.response?.data?.error || 'Failed to update movie' });
    }
  };

  const handleDeleteMovie = async () => {
    if (!window.confirm(`Delete "${selectedMovie.title}" from ALL circles? This cannot be undone.`)) {
      return;
    }

    try {
      const response = await client.delete(`/api/admin/movies/${selectedMovie.id}`);
      setMovieMessage({ type: 'success', text: response.data.message });
      setSelectedMovie(null);
      searchMovies();
    } catch (err) {
      console.error('Error deleting movie:', err);
      setMovieMessage({ type: 'error', text: err.response?.data?.error || 'Failed to delete movie' });
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
      setMovieMessage({ type: 'error', text: 'Failed to search OMDB' });
    } finally {
      setSearchingOmdb(false);
    }
  };

  const handleReplaceWithMovie = async (omdbMovie) => {
    if (!window.confirm(`Replace "${replacingMovie.title}" with "${omdbMovie.Title}"? This will clear all swipes on the old movie.`)) {
      return;
    }

    try {
      const response = await client.post(`/api/admin/movies/${replacingMovie.id}/replace`, omdbMovie);
      setMovieMessage({
        type: 'success',
        text: `Replaced "${response.data.old_movie}" with "${response.data.new_movie.title}". ${response.data.circles_transferred} circles updated, ${response.data.swipes_cleared} swipes cleared.`
      });
      setReplacingMovie(null);
      setOmdbResults([]);
      setSelectedMovie(null);
      searchMovies();
    } catch (err) {
      console.error('Error replacing movie:', err);
      setMovieMessage({ type: 'error', text: err.response?.data?.error || 'Failed to replace movie' });
    }
  };

  if (loading) {
    return <div className="admin-container"><p>Loading admin data...</p></div>;
  }

  if (error) {
    return <div className="admin-container"><p className="error">{error}</p></div>;
  }

  return (
    <div className="admin-container">
      <h2>Site Administration</h2>

      <div className="admin-tabs">
        <button
          className={`admin-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={`admin-tab ${activeTab === 'movies' ? 'active' : ''}`}
          onClick={() => setActiveTab('movies')}
        >
          Movies
        </button>
      </div>

      {activeTab === 'overview' && (
        <>
          <section className="admin-section">
            <h3>Global Analytics</h3>
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-value">{analytics?.total_users || 0}</span>
            <span className="stat-label">Total Users</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{analytics?.total_circles || 0}</span>
            <span className="stat-label">Total Circles</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{analytics?.total_movies || 0}</span>
            <span className="stat-label">Total Movies</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{analytics?.active_circles_7d || 0}</span>
            <span className="stat-label">Active Circles (7d)</span>
          </div>
        </div>
      </section>

      <section className="admin-section">
        <h3>All Circles</h3>
        <p className="hint">Click a circle to view its members</p>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Members</th>
              <th>Movies</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {circles.map(circle => (
              <tr
                key={circle.id}
                onClick={() => handleCircleClick(circle)}
                className={`clickable ${selectedCircle?.id === circle.id ? 'selected' : ''}`}
              >
                <td>{circle.name}</td>
                <td>{circle.member_count}</td>
                <td>{circle.movie_count}</td>
                <td>{new Date(circle.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {selectedCircle && (
          <div className="members-panel">
            <h4>Members of "{selectedCircle.name}"</h4>
            {loadingMembers ? (
              <p>Loading members...</p>
            ) : members.length === 0 ? (
              <p>No members found</p>
            ) : (
              <table className="admin-table members-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map(member => (
                    <tr key={member.id}>
                      <td>{member.display_name || '-'}</td>
                      <td>{member.email}</td>
                      <td><span className={`role-badge ${member.role}`}>{member.role}</span></td>
                      <td>{new Date(member.joined_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </section>

      <section className="admin-section">
            <h3>Actions</h3>
            <button
              className="admin-action-btn"
              onClick={handleSeedCircles}
              disabled={seeding}
            >
              {seeding ? 'Seeding...' : 'Seed All Circles with Movies'}
            </button>
            {seedMessage && <p className="seed-message">{seedMessage}</p>}
          </section>
        </>
      )}

      {activeTab === 'movies' && (
        <>
          <section className="admin-section">
            <h3>Search Movies</h3>
            <p className="hint">Search for movies in the database to edit, replace, or delete them</p>
            <div className="movie-search-row">
              <input
                type="text"
                value={movieSearch}
                onChange={(e) => setMovieSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && searchMovies()}
                placeholder="Search by title..."
                className="movie-search-input"
              />
              <button
                className="admin-action-btn"
                onClick={searchMovies}
                disabled={loadingMovies}
              >
                {loadingMovies ? 'Searching...' : 'Search'}
              </button>
            </div>

            {movieMessage && (
              <p className={`movie-message ${movieMessage.type}`}>{movieMessage.text}</p>
            )}

            {movies.length > 0 && (
              <table className="admin-table movies-table">
                <thead>
                  <tr>
                    <th>Poster</th>
                    <th>Title</th>
                    <th>Year</th>
                    <th>Circles</th>
                  </tr>
                </thead>
                <tbody>
                  {movies.map(movie => (
                    <tr
                      key={movie.id}
                      onClick={() => handleMovieClick(movie)}
                      className={`clickable ${selectedMovie?.id === movie.id ? 'selected' : ''}`}
                    >
                      <td>
                        <img
                          src={movie.poster}
                          alt={movie.title}
                          className="movie-poster-thumb"
                          onError={(e) => { e.target.style.display = 'none'; }}
                        />
                      </td>
                      <td>{movie.title}</td>
                      <td>{movie.year}</td>
                      <td>{movie.circle_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {selectedMovie && !editingMovie && !replacingMovie && (
            <section className="admin-section movie-details">
              <h3>Movie Details</h3>
              <div className="movie-detail-card">
                <div className="movie-detail-header">
                  <img
                    src={selectedMovie.poster}
                    alt={selectedMovie.title}
                    className="movie-poster-large"
                    onError={(e) => { e.target.style.display = 'none'; }}
                  />
                  <div className="movie-detail-info">
                    <h4>{selectedMovie.title} ({selectedMovie.year})</h4>
                    <p className="movie-meta">{selectedMovie.genre} | {selectedMovie.length} | Rating: {selectedMovie.rating}</p>
                    <p className="movie-description">{selectedMovie.description}</p>
                    <p className="movie-starring"><strong>Starring:</strong> {selectedMovie.starring}</p>
                    <p className="movie-circles"><strong>In {selectedMovie.circle_count} circle(s)</strong></p>
                  </div>
                </div>
                <div className="movie-actions">
                  <button className="admin-action-btn" onClick={handleEditMovie}>Edit</button>
                  <button className="admin-action-btn secondary" onClick={handleStartReplace}>Replace</button>
                  <button className="admin-action-btn danger" onClick={handleDeleteMovie}>Delete</button>
                </div>
              </div>
            </section>
          )}

          {editingMovie && (
            <section className="admin-section movie-edit">
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
                <div className="edit-actions">
                  <button className="admin-action-btn" onClick={handleSaveMovie}>Save</button>
                  <button className="admin-action-btn secondary" onClick={() => setEditingMovie(null)}>Cancel</button>
                </div>
              </div>
            </section>
          )}

          {replacingMovie && (
            <section className="admin-section movie-replace">
              <h3>Replace "{replacingMovie.title}"</h3>
              <p className="hint">Search OMDB to find the correct movie</p>
              <div className="movie-search-row">
                <input
                  type="text"
                  value={omdbSearch}
                  onChange={(e) => setOmdbSearch(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && searchOmdb()}
                  placeholder="Search OMDB..."
                  className="movie-search-input"
                />
                <button
                  className="admin-action-btn"
                  onClick={searchOmdb}
                  disabled={searchingOmdb}
                >
                  {searchingOmdb ? 'Searching...' : 'Search OMDB'}
                </button>
                <button className="admin-action-btn secondary" onClick={() => setReplacingMovie(null)}>Cancel</button>
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
                        className="admin-action-btn"
                        onClick={() => handleReplaceWithMovie(movie)}
                      >
                        Use This
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}

export default Admin;
