import React, { useState } from 'react';
import axios from 'axios';
import './AddMovie.css';

const AddMovie = () => {
  const [query, setQuery] = useState('');
  const [movie, setMovie] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [addSuccess, setAddSuccess] = useState(false);
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';


  const searchMovie = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMovie(null);
    setAddSuccess(false);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/movies/search?query=${encodeURIComponent(query)}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMovie(response.data);
    } catch (error) {
      console.error('Error searching movie:', error);
      setError('Failed to search movie. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const addMovie = async () => {
    setLoading(true);
    setError(null);
    setAddSuccess(false);

    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/api/movies/add`, movie, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAddSuccess(true);
    } catch (error) {
      console.error('Error adding movie:', error);
      setError('Failed to add movie. It might already exist in the database.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="add-movie-container">
      <h2>Add a New Movie</h2>
      <form onSubmit={searchMovie} className="search-form">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter movie title"
          required
        />
        <button type="submit">Search</button>
      </form>

      {loading && <div className="loading">Loading...</div>}
      {error && <div className="error">{error}</div>}
      {addSuccess && <div className="success">Movie added successfully!</div>}

      {movie && (
        <div className="movie-details">
          <img src={movie.Poster} alt={movie.Title} />
          <h3>{movie.Title}</h3>
          <p><strong>Year:</strong> {movie.Year}</p>
          <p><strong>Director:</strong> {movie.Director}</p>
          <p><strong>Genre:</strong> {movie.Genre}</p>
          <p><strong>Plot:</strong> {movie.Plot}</p>
          <button onClick={addMovie}>Add to Database</button>
        </div>
      )}
    </div>
  );
};

export default AddMovie;