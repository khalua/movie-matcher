import React, { useState, useEffect } from 'react';
import client from './api/client';
import { useCircle } from './contexts/CircleContext';
import './AddMovie.css';

const AddMovie = ({ user }) => {
  const [query, setQuery] = useState('');
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [addSuccess, setAddSuccess] = useState({});
  const [selectedCircles, setSelectedCircles] = useState([]);
  const [addToAllCircles, setAddToAllCircles] = useState(false);
  const { currentCircle } = useCircle();
  const isSiteAdmin = user?.is_site_admin;

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
      <h2>Add New Movies</h2>
      <form onSubmit={searchMovies} className="search-form">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter movie titles separated by semicolons"
          required
        />
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
        <div key={movie.imdbID} className="movie-details">
          <img src={movie.Poster} alt={movie.Title} />
          <h3>{movie.Title}</h3>
          <p><strong>Year:</strong> {movie.Year}</p>
          {movie.streaming && movie.streaming.length > 0 && (
            <div className="streaming-info">
              <span className="streaming-label">Streaming on:</span>
              {movie.streaming.map((service, index) => (
                <span key={index} className="streaming-badge">{service}</span>
              ))}
            </div>
          )}
          <p><strong>Director:</strong> {movie.Director}</p>
          <p><strong>Genre:</strong> {movie.Genre}</p>
          <p><strong>Plot:</strong> {movie.Plot}</p>
          {addSuccess[movie.imdbID] ? (
            <div className="success">Added successfully!</div>
          ) : movie.alreadyInDatabase ? (
            <button disabled className="already-exists">Already in Database</button>
          ) : (
            <button onClick={() => addMovie(movie)}>Add to Database</button>
          )}
        </div>
      ))}
    </div>
  );
};

export default AddMovie;