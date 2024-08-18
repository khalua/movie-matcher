import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './AllMovies.css';

const AllMovies = () => {
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';

  useEffect(() => {
    fetchAllMovies();
  }, []);

  const fetchAllMovies = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${apiUrl}/api/movies/all`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMovies(response.data);
    } catch (error) {
      console.error('Error fetching all movies:', error);
      setError('Failed to fetch movies. Please try again.');
    } finally {
      setLoading(false);
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
      <h2>All Movies</h2>
      <table className="movies-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Year</th>
            <th>Genre</th>
            <th>Rating</th>
            <th>Added By</th>
            <th>Not Reviewed By</th>
          </tr>
        </thead>
        <tbody>
          {movies.map(movie => (
            <tr key={movie.id}>
              <td>{movie.title}</td>
              <td>{movie.year}</td>
              <td>{movie.genre}</td>
              <td>{movie.rating}</td>
              <td>{movie.added_by ? movie.added_by.username : 'Unknown'}</td>
              <td>
                {movie.unseen_by.length > 0 ? (
                  <ul className="unseen-users-list">
                    {movie.unseen_by.map(user => (
                      <li key={user.id}>{user.username}</li>
                    ))}
                  </ul>
                ) : (
                  "Seen by all"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AllMovies;