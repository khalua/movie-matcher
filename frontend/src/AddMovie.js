import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import client from './api/client';
import { useCircle } from './contexts/CircleContext';
import './AddMovie.css';

const AddMovie = ({ user }) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]); // List of movies from search
  const [selectedMovie, setSelectedMovie] = useState(null); // Full details of selected movie
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [addSuccess, setAddSuccess] = useState({});
  const [selectedCircles, setSelectedCircles] = useState([]);
  const [addToAllCircles, setAddToAllCircles] = useState(false);
  const { currentCircle } = useCircle();
  const isSiteAdmin = user?.is_site_admin;
  const isCircleAdmin = currentCircle?.role === 'admin';
  const canAddPacks = isCircleAdmin || isSiteAdmin;

  useEffect(() => {
    if (currentCircle) {
      setSelectedCircles([currentCircle.id]);
    }
  }, [currentCircle]);

  const searchMovies = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSearchResults([]);
    setSelectedMovie(null);
    setAddSuccess({});

    try {
      const response = await client.get(`/api/movies/search?query=${encodeURIComponent(query)}`);
      setSearchResults(response.data);
    } catch (error) {
      console.error('Error searching movies:', error);
      setError('No movies found matching your search.');
    } finally {
      setLoading(false);
    }
  };

  const selectMovie = async (imdbID) => {
    setLoading(true);
    setError(null);

    try {
      const response = await client.get(`/api/movies/details/${imdbID}`);
      setSelectedMovie(response.data);
      setSearchResults([]); // Clear search results after selection
    } catch (error) {
      console.error('Error fetching movie details:', error);
      setError('Failed to load movie details.');
    } finally {
      setLoading(false);
    }
  };

  const clearSelection = () => {
    setSelectedMovie(null);
    // Re-run the search to show results again
    if (query) {
      setLoading(true);
      client.get(`/api/movies/search?query=${encodeURIComponent(query)}`)
        .then(response => setSearchResults(response.data))
        .catch(() => setSearchResults([]))
        .finally(() => setLoading(false));
    }
  };

  const addMovie = async (movie) => {
    setLoading(true);
    setError(null);

    try {
      if (addToAllCircles && isSiteAdmin) {
        // Site admin adding to all circles
        await client.post('/api/admin/add-movie-all-circles', movie);
      } else {
        // Regular add to selected circles
        await client.post('/api/movies/add', {
          ...movie,
          circle_ids: selectedCircles
        });
      }
      setAddSuccess(prev => ({ ...prev, [movie.imdbID]: true }));
    } catch (error) {
      console.error('Error adding movie:', error);
      setError(`Failed to add "${movie.Title}". It might already exist in the database.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="add-movie-container">
      <h2>Add Movies to {currentCircle?.name || 'Circle'}</h2>

      {canAddPacks && (
        <div className="movie-packs-section">
          <h3>Movie Packs</h3>
          <p className="section-description">
            Quickly add curated collections of movies to your Circle.
          </p>
          <button
            className="browse-packs-btn"
            onClick={() => navigate('/packs')}
          >
            Browse Movie Packs
          </button>
        </div>
      )}

      <div className="search-section">
        <h3>Search & Add</h3>
        <p className="section-description">
          Search for specific movies to add to your Circle.
        </p>
      </div>

      <form onSubmit={searchMovies} className="search-form">
        <div className="input-group">
          <label htmlFor="movie-search">Movie Title</label>
          <input
            id="movie-search"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter movie titles separated by semicolons"
            required
          />
        </div>
        <button type="submit">Search</button>
      </form>

      {isSiteAdmin && (
        <div className="admin-option">
          <label>
            <input
              type="checkbox"
              checked={addToAllCircles}
              onChange={(e) => setAddToAllCircles(e.target.checked)}
            />
            Add to all Circles (as "Movie Matcher")
          </label>
        </div>
      )}

      {loading && <div className="loading">Loading...</div>}
      {error && <div className="error">{error}</div>}

      {/* Search Results - Multiple movies to choose from */}
      {searchResults.length > 0 && !selectedMovie && (
        <div className="search-results">
          <h3 className="results-header">Select a Movie ({searchResults.length} results)</h3>
          {searchResults.map((movie) => (
            <div
              key={movie.imdbID}
              className={`search-result-item ${movie.alreadyInDatabase ? 'already-in-db' : ''}`}
              onClick={() => !movie.alreadyInDatabase && selectMovie(movie.imdbID)}
            >
              <img
                src={movie.Poster !== 'N/A' ? movie.Poster : 'https://via.placeholder.com/60x90?text=No+Poster'}
                alt={movie.Title}
              />
              <div className="result-info">
                <h4>{movie.Title}</h4>
                <p className="result-year">{movie.Year}</p>
              </div>
              {movie.alreadyInDatabase && (
                <span className="in-db-badge">Already Added</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Selected Movie - Full details view */}
      {selectedMovie && (
        <div className="movie-details">
          <button className="back-btn" onClick={clearSelection}>
            ← Back to Results
          </button>
          <div className="movie-header">
            <img
              src={selectedMovie.Poster !== 'N/A' ? selectedMovie.Poster : 'https://via.placeholder.com/200x300?text=No+Poster'}
              alt={selectedMovie.Title}
            />
            <div className="movie-info">
              <h3>{selectedMovie.Title}</h3>
              <p className="movie-meta">{selectedMovie.Year} • {selectedMovie.Genre}</p>
              <p className="movie-meta">{selectedMovie.Runtime} • {selectedMovie.Rated}</p>
              <p className="movie-rating">IMDb: {selectedMovie.imdbRating}/10</p>
              {selectedMovie.streaming && selectedMovie.streaming.length > 0 && (
                <div className="streaming-badges">
                  {selectedMovie.streaming.map((service, index) => (
                    <span key={index} className="streaming-badge">{service}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
          <p className="movie-plot">{selectedMovie.Plot}</p>
          <p className="movie-starring"><strong>Starring:</strong> {selectedMovie.Actors}</p>
          <p className="movie-director"><strong>Director:</strong> {selectedMovie.Director}</p>

          {addSuccess[selectedMovie.imdbID] ? (
            <div className="success">Added successfully!</div>
          ) : selectedMovie.alreadyInDatabase ? (
            <button disabled className="already-exists">Already in Circle</button>
          ) : (
            <button onClick={() => addMovie(selectedMovie)}>
              Add to the {currentCircle?.name || 'Circle'}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default AddMovie;