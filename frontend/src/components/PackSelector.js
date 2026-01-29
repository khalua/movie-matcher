import React, { useState, useEffect } from 'react';
import client from '../api/client';
import { useCircle } from '../contexts/CircleContext';
import './PackSelector.css';

const PackSelector = ({ onClose, onPackAdded, embedded = false }) => {
  const { currentCircle } = useCircle();
  const [packs, setPacks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [previewPack, setPreviewPack] = useState(null);
  const [previewMovies, setPreviewMovies] = useState([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [addingPack, setAddingPack] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    fetchPacks();
  }, []);

  const fetchPacks = async () => {
    try {
      setLoading(true);
      const response = await client.get('/api/packs');
      setPacks(response.data.packs || []);
    } catch (err) {
      setError('Failed to load movie packs');
      console.error('Error fetching packs:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPackPreview = async (pack) => {
    try {
      setPreviewLoading(true);
      setPreviewPack(pack);
      setError(null);
      const response = await client.get(
        `/api/packs/${pack.id}/preview?circle_id=${currentCircle.id}`
      );
      setPreviewMovies(response.data.movies || []);
    } catch (err) {
      const errorMessage = err.response?.data?.error ||
        `Unable to load ${pack.name}. Please try a different pack.`;
      setError(errorMessage);
      setPreviewPack(null);
      console.error('Error fetching pack preview:', err);
    } finally {
      setPreviewLoading(false);
    }
  };

  const addPackToCircle = async (pack) => {
    try {
      setAddingPack(pack.id);
      setError(null);
      const response = await client.post(`/api/packs/${pack.id}/add-to-circle`, {
        circle_id: currentCircle.id
      });
      setSuccess(`Added ${response.data.added_count} movies from ${pack.name}!`);
      if (onPackAdded) {
        onPackAdded(response.data);
      }
      // Refresh packs to update counts
      fetchPacks();
      // Close preview if open
      setPreviewPack(null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to add pack');
      console.error('Error adding pack:', err);
    } finally {
      setAddingPack(null);
    }
  };

  const categories = [
    { id: 'all', label: 'All Packs' },
    { id: 'streaming', label: 'Streaming' },
    { id: 'genre', label: 'Genres' },
    { id: 'curated', label: 'Curated' }
  ];

  const filteredPacks = selectedCategory === 'all'
    ? packs
    : packs.filter(p => p.category === selectedCategory);

  const closePreview = () => {
    setPreviewPack(null);
    setPreviewMovies([]);
  };

  if (loading) {
    if (embedded) {
      return <div className="pack-selector-loading">Loading movie packs...</div>;
    }
    return (
      <div className="pack-selector-overlay">
        <div className="pack-selector-modal">
          <div className="pack-selector-loading">Loading movie packs...</div>
        </div>
      </div>
    );
  }

  const content = (
    <>
      {!embedded && (
        <div className="pack-selector-header">
          <h2>Add Movie Packs</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>
      )}

        {error && <div className="pack-error">{error}</div>}
        {success && <div className="pack-success">{success}</div>}

        {previewPack ? (
          <div className="pack-preview">
            <div className="preview-header">
              <button className="back-btn" onClick={closePreview}>
                &larr; Back to Packs
              </button>
              <h3>{previewPack.icon} {previewPack.name}</h3>
            </div>

            {previewLoading ? (
              <div className="preview-loading">Loading movies...</div>
            ) : (
              <>
                <div className="preview-stats">
                  <span>{previewMovies.length} movies</span>
                  <span className="separator">|</span>
                  <span>
                    {previewMovies.filter(m => m.already_in_circle).length} already in circle
                  </span>
                </div>

                <div className="preview-actions">
                  <button
                    className="add-pack-btn primary"
                    onClick={() => addPackToCircle(previewPack)}
                    disabled={addingPack === previewPack.id}
                  >
                    {addingPack === previewPack.id ? 'Adding...' : `Add ${previewPack.name} to Circle`}
                  </button>
                </div>

                <div className="preview-movies">
                  {previewMovies.map(movie => (
                    <div
                      key={movie.id}
                      className={`preview-movie ${movie.already_in_circle ? 'in-circle' : ''}`}
                    >
                      <div className="poster-wrapper">
                        {movie.poster ? (
                          <img
                            src={movie.poster}
                            alt={movie.title}
                            onError={(e) => {
                              e.target.style.display = 'none';
                            }}
                          />
                        ) : (
                          <div className="poster-placeholder">🎬</div>
                        )}
                      </div>
                      <div className="movie-info">
                        <span className="movie-title">{movie.title}</span>
                        <span className="movie-year">{movie.year}</span>
                        {movie.already_in_circle && (
                          <span className="in-circle-badge">In Circle</span>
                        )}
                        {movie.user_has_swiped && (
                          <span className={`swipe-badge ${movie.user_swipe_action}`}>
                            {movie.user_swipe_action === 'like' ? 'Liked' : 'Passed'}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        ) : (
          <>
            <div className="category-tabs">
              {categories.map(cat => (
                <button
                  key={cat.id}
                  className={`category-tab ${selectedCategory === cat.id ? 'active' : ''}`}
                  onClick={() => setSelectedCategory(cat.id)}
                >
                  {cat.label}
                </button>
              ))}
            </div>

            <div className="packs-grid">
              {filteredPacks.map(pack => (
                <div key={pack.id} className="pack-card">
                  <div className="pack-icon">{pack.icon}</div>
                  <h3 className="pack-name">{pack.name}</h3>
                  <p className="pack-description">{pack.description}</p>
                  <div className="pack-meta">
                    <span className="pack-count">
                      {pack.movie_count || '~'} movies
                    </span>
                  </div>
                  {pack.preview_posters?.length > 0 && (
                    <div className="pack-posters">
                      {pack.preview_posters.slice(0, 3).map((poster, i) => (
                        <img
                          key={i}
                          src={poster}
                          alt=""
                          className="mini-poster"
                          onError={(e) => { e.target.style.display = 'none'; }}
                        />
                      ))}
                    </div>
                  )}
                  <div className="pack-actions">
                    <button
                      className="preview-btn"
                      onClick={() => fetchPackPreview(pack)}
                    >
                      Preview
                    </button>
                    <button
                      className="add-btn"
                      onClick={() => addPackToCircle(pack)}
                      disabled={addingPack === pack.id}
                    >
                      {addingPack === pack.id ? 'Adding...' : 'Add'}
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {filteredPacks.length === 0 && (
              <div className="no-packs">
                No packs available in this category.
              </div>
            )}
          </>
        )}

        <div className="pack-selector-footer">
          <small>Streaming data provided by JustWatch via TMDB</small>
        </div>
      </>
    );

  if (embedded) {
    return <div className="pack-selector-embedded">{content}</div>;
  }

  return (
    <div className="pack-selector-overlay" onClick={onClose}>
      <div className="pack-selector-modal" onClick={e => e.stopPropagation()}>
        {content}
      </div>
    </div>
  );
};

export default PackSelector;
