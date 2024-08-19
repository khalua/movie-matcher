import React, { useState } from 'react';
import axios from 'axios';
import './AddMovie.css';

const AddMovie = () => {
  const [query, setQuery] = useState('');
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [addSuccess, setAddSuccess] = useState({});
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

  const searchMovies = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMovies([]);
    setAddSuccess({});

    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/movies/search?query=${encodeURIComponent(query)}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
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
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/api/movies/add`, movie, {
        headers: { Authorization: `Bearer ${token}` }
      });
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

      {loading && <div className="loading">Loading...</div>}
      {error && <div className="error">{error}</div>}

      {movies.map((movie) => (
        <div key={movie.imdbID} className="movie-details">
          <img src={movie.Poster} alt={movie.Title} />
          <h3>{movie.Title}</h3>
          <p><strong>Year:</strong> {movie.Year}</p>
          <p><strong>Director:</strong> {movie.Director}</p>
          <p><strong>Genre:</strong> {movie.Genre}</p>
          <p><strong>Plot:</strong> {movie.Plot}</p>
          {addSuccess[movie.imdbID] ? (
            <div className="success">Added successfully!</div>
          ) : (
            <button onClick={() => addMovie(movie)}>Add to Database</button>
          )}
        </div>
      ))}
    </div>
  );
};

export default AddMovie;