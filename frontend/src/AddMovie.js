import React, { useState, useEffect } from 'react';
import client from './api/client';
import { useCircle } from './contexts/CircleContext';
import PackSelector from './components/PackSelector';
import './AddMovie.css';

const AddMovie = ({ user }) => {
  const [query, setQuery] = useState('');
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [addSuccess, setAddSuccess] = useState({});
  const [selectedCircles, setSelectedCircles] = useState([]);
  const [addToAllCircles, setAddToAllCircles] = useState(false);
  const [showPackSelector, setShowPackSelector] = useState(false);
  const [packSuccess, setPackSuccess] = useState(null);
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
    setMovies([]);
    setAddSuccess({});

    try {
      const response = await client.get(`/api/movies/search?query=${encodeURIComponent(query)}`);
      setMovies(response.data);
    } catch (error) {
      console.error('Error searching movies:', error);
      setError('Movie not found.');
    } finally {
      setLoading(false);
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
      <h2>Add Movies</h2>

      {canAddPacks && (
        <div className="movie-packs-section">
          <h3>Movie Packs</h3>
          <p className="section-description">
            Quickly add curated collections of movies to your circle.
          </p>
          {packSuccess && <div className="success">{packSuccess}</div>}
          <button
            className="browse-packs-btn"
            onClick={() => setShowPackSelector(true)}
          >
            Browse Movie Packs
          </button>
        </div>
      )}

      {showPackSelector && (
        <PackSelector
          onClose={() => setShowPackSelector(false)}
          onPackAdded={(result) => {
            setPackSuccess(result.message);
            setTimeout(() => setPackSuccess(null), 5000);
          }}
        />
      )}

      <div className="search-section">
        <h3>Search & Add</h3>
        <p className="section-description">
          Search for specific movies to add to your circle.
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
            Add to all circles (as "Movie Matcher")
          </label>
        </div>
      )}

      {loading && <div className="loading">Loading...</div>}
      {error && <div className="error">{error}</div>}

      {movies.map((movie) => (
        <div key={movie.imdbID} className="movie-details compact">
          <div className="movie-header">
            <img src={movie.Poster} alt={movie.Title} />
            <div className="movie-info">
              <h3>{movie.Title}</h3>
              <p className="movie-meta">{movie.Year} • {movie.Genre}</p>
              {movie.streaming && movie.streaming.length > 0 && (
                <div className="streaming-badges">
                  {movie.streaming.map((service, index) => (
                    <span key={index} className="streaming-badge">{service}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
          {addSuccess[movie.imdbID] ? (
            <div className="success">Added successfully!</div>
          ) : movie.alreadyInDatabase ? (
            <button disabled className="already-exists">Already in Circle</button>
          ) : (
            <button onClick={() => addMovie(movie)}>
              Add to the {currentCircle?.name || 'Circle'}
            </button>
          )}
        </div>
      ))}
    </div>
  );
};

export default AddMovie;