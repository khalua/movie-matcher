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

  // User management state
  const [users, setUsers] = useState([]);
  const [userSearch, setUserSearch] = useState('');
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [userMessage, setUserMessage] = useState(null);

  // API Utilization state
  const [showApiUtilization, setShowApiUtilization] = useState(false);
  const [apiUtilization, setApiUtilization] = useState(null);
  const [loadingApiUtilization, setLoadingApiUtilization] = useState(false);

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

  // User management functions
  const searchUsers = async () => {
    setLoadingUsers(true);
    setUserMessage(null);
    try {
      const response = await client.get(`/api/admin/users?search=${encodeURIComponent(userSearch)}`);
      setUsers(response.data);
    } catch (err) {
      console.error('Error fetching users:', err);
      setUserMessage({ type: 'error', text: 'Failed to load users' });
    } finally {
      setLoadingUsers(false);
    }
  };

  const handleDeleteUser = async (user) => {
    if (!window.confirm(`Delete user "${user.email}"? This will remove them from all circles and delete their swipes. This cannot be undone.`)) {
      return;
    }

    try {
      const response = await client.delete(`/api/admin/users/${user.id}`);
      setUserMessage({ type: 'success', text: response.data.message });
      searchUsers();
      fetchAdminData();
    } catch (err) {
      console.error('Error deleting user:', err);
      setUserMessage({ type: 'error', text: err.response?.data?.error || 'Failed to delete user' });
    }
  };

  // API Utilization function
  const fetchApiUtilization = async () => {
    setLoadingApiUtilization(true);
    setShowApiUtilization(true);
    try {
      const response = await client.get('/api/admin/api-utilization');
      setApiUtilization(response.data);
    } catch (err) {
      console.error('Error fetching API utilization:', err);
      setApiUtilization({ error: 'Failed to fetch API utilization' });
    } finally {
      setLoadingApiUtilization(false);
    }
  };

  // Circle delete function
  const handleDeleteCircle = async (circle) => {
    if (!window.confirm(`Delete circle "${circle.name}"? This will remove all members, movies, and swipes. This cannot be undone.`)) {
      return;
    }

    try {
      const response = await client.delete(`/api/admin/circles/${circle.id}`);
      setSeedMessage(response.data.message);
      setSelectedCircle(null);
      setMembers([]);
      fetchAdminData();
    } catch (err) {
      console.error('Error deleting circle:', err);
      setSeedMessage(err.response?.data?.error || 'Failed to delete circle');
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
          className={`admin-tab ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => { setActiveTab('users'); if (users.length === 0) searchUsers(); }}
        >
          Users
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
              <th>Actions</th>
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
                <td>
                  <button
                    className="admin-action-btn danger small"
                    onClick={(e) => { e.stopPropagation(); handleDeleteCircle(circle); }}
                  >
                    Delete
                  </button>
                </td>
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
            <div className="admin-actions-row">
              <button
                className="admin-action-btn"
                onClick={handleSeedCircles}
                disabled={seeding}
              >
                {seeding ? 'Seeding...' : 'Seed All Circles with Movies'}
              </button>
              <button
                className="admin-action-btn secondary"
                onClick={fetchApiUtilization}
                disabled={loadingApiUtilization}
              >
                {loadingApiUtilization ? 'Loading...' : 'API Utilization'}
              </button>
            </div>
            {seedMessage && <p className="seed-message">{seedMessage}</p>}
          </section>
        </>
      )}

      {/* API Utilization Modal */}
      {showApiUtilization && (
        <div className="modal-overlay" onClick={() => setShowApiUtilization(false)}>
          <div className="api-utilization-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>API Utilization</h3>
              <button className="close-btn" onClick={() => setShowApiUtilization(false)}>&times;</button>
            </div>

            {loadingApiUtilization ? (
              <div className="modal-content">
                <p>Loading API utilization data...</p>
              </div>
            ) : apiUtilization?.error ? (
              <div className="modal-content">
                <p className="error">{apiUtilization.error}</p>
              </div>
            ) : apiUtilization ? (
              <div className="modal-content">
                {/* OMDB Section */}
                <div className="api-section">
                  <h4>OMDB (Open Movie Database)</h4>
                  <div className="api-stats">
                    <div className="usage-bar-container">
                      <div className="usage-bar" style={{ width: `${apiUtilization.omdb?.today?.percentage || 0}%` }}></div>
                    </div>
                    <div className="usage-numbers">
                      <span className="usage-current">{apiUtilization.omdb?.today?.calls || 0}</span>
                      <span className="usage-divider">/</span>
                      <span className="usage-limit">{apiUtilization.omdb?.today?.limit || 1000}</span>
                      <span className="usage-label">calls today ({apiUtilization.omdb?.today?.percentage || 0}%)</span>
                    </div>
                    <p className="reset-time">Resets: {apiUtilization.omdb?.limit_info?.reset_time}</p>
                  </div>
                  {apiUtilization.omdb?.this_week?.length > 0 && (
                    <div className="weekly-usage">
                      <h5>Last 7 Days</h5>
                      <div className="weekly-bars">
                        {apiUtilization.omdb.this_week.map((day, idx) => (
                          <div key={idx} className="day-bar">
                            <div
                              className="day-fill"
                              style={{ height: `${Math.min(100, (day.calls / 1000) * 100)}%` }}
                              title={`${day.date}: ${day.calls} calls`}
                            ></div>
                            <span className="day-label">{new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' })}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* TMDB Section */}
                <div className="api-section">
                  <h4>TMDB (The Movie Database)</h4>
                  <div className="api-stats">
                    <div className="usage-bar-container">
                      <div className="usage-bar tmdb" style={{ width: `${apiUtilization.tmdb?.today?.percentage || 0}%` }}></div>
                    </div>
                    <div className="usage-numbers">
                      <span className="usage-current">{apiUtilization.tmdb?.today?.calls || 0}</span>
                      <span className="usage-divider">/</span>
                      <span className="usage-limit">{apiUtilization.tmdb?.today?.limit || 1000}</span>
                      <span className="usage-label">calls today ({apiUtilization.tmdb?.today?.percentage || 0}%)</span>
                    </div>
                    <p className="reset-time">Limits: {apiUtilization.tmdb?.limit_info?.reset_time}</p>
                    {apiUtilization.tmdb?.alert_triggered && (
                      <p className="api-alert">Alert threshold reached!</p>
                    )}
                  </div>
                  {apiUtilization.tmdb?.this_week?.length > 0 && (
                    <div className="weekly-usage">
                      <h5>Last 7 Days</h5>
                      <div className="weekly-bars">
                        {apiUtilization.tmdb.this_week.map((day, idx) => (
                          <div key={idx} className="day-bar">
                            <div
                              className="day-fill tmdb"
                              style={{ height: `${Math.min(100, (day.calls / 1000) * 100)}%` }}
                              title={`${day.date}: ${day.calls} calls`}
                            ></div>
                            <span className="day-label">{new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' })}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <p className="fetched-at">Last fetched: {apiUtilization.fetched_at ? new Date(apiUtilization.fetched_at).toLocaleString() : 'N/A'}</p>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {activeTab === 'users' && (
        <>
          <section className="admin-section">
            <h3>Manage Users</h3>
            <p className="hint">Search for users by email or display name</p>
            <div className="movie-search-row">
              <input
                type="text"
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && searchUsers()}
                placeholder="Search by email or name..."
                className="movie-search-input"
              />
              <button
                className="admin-action-btn"
                onClick={searchUsers}
                disabled={loadingUsers}
              >
                {loadingUsers ? 'Searching...' : 'Search'}
              </button>
            </div>

            {userMessage && (
              <p className={`movie-message ${userMessage.type}`}>{userMessage.text}</p>
            )}

            {users.length > 0 && (
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Display Name</th>
                    <th>Circles</th>
                    <th>Circle Admin</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(u => (
                    <tr key={u.id}>
                      <td>{u.email}</td>
                      <td>{u.display_name || '-'}</td>
                      <td>{u.circle_count}</td>
                      <td>
                        {u.admin_circles && u.admin_circles.length > 0 ? (
                          <span className="circle-admin-list">
                            {u.admin_circles.map(c => c.name).join(', ')}
                          </span>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td>{new Date(u.created_at).toLocaleDateString()}</td>
                      <td>
                        {u.is_site_admin ? (
                          <span className="hint">Protected</span>
                        ) : (
                          <button
                            className="admin-action-btn danger small"
                            onClick={() => handleDeleteUser(u)}
                          >
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
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
