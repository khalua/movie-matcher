import React, { useState, useEffect } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import client from '../api/client';
import './LandingPage.css';

const LandingPage = ({
  onGetStarted,
  onSignIn,
  onGoogleSuccess,
  onGoogleError,
  error
}) => {
  const [posters, setPosters] = useState([]);
  const [recentlyWatched, setRecentlyWatched] = useState([]);

  useEffect(() => {
    const fetchPosters = async () => {
      try {
        const response = await client.get('/api/movies/landing-posters');
        if (response.data.posters && response.data.posters.length > 0) {
          setPosters(response.data.posters);
        }
      } catch (err) {
        console.error('Failed to fetch landing posters:', err);
      }
    };

    const fetchRecentlyWatched = async () => {
      try {
        const response = await client.get('/api/movies/landing-recently-watched');
        if (response.data.movies && response.data.movies.length > 0) {
          setRecentlyWatched(response.data.movies);
        }
      } catch (err) {
        console.error('Failed to fetch recently watched:', err);
      }
    };

    fetchPosters();
    fetchRecentlyWatched();
  }, []);

  // Get posters for the card stack (use first 3, or fewer if not available)
  const cardPosters = posters.slice(0, 3);

  return (
    <div className="landing-page">
      {/* Header */}
      <header className="landing-header">
        <div className="landing-header-brand">
          <img src="/mm-logo.png" alt="Movie Matcher" className="landing-header-logo" />
          <span className="landing-header-name">Movie Matcher</span>
        </div>
        <div className="landing-header-actions">
          <button className="landing-btn-secondary" onClick={onSignIn}>
            Sign In
          </button>
          <button className="landing-btn-primary" onClick={onGetStarted}>
            Get Started
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="landing-hero">
        <div className="landing-hero-content">
          <h1 className="landing-hero-title">
            End Movie Night<br />Arguments. Forever.
          </h1>
          <p className="landing-hero-subtitle">
            Swipe on movies you love. When everyone in your group matches, you've found your next watch.
          </p>
          <div className="landing-hero-cta">
            <button className="landing-btn-primary landing-btn-large" onClick={onGetStarted}>
              Get Started — It's Free
            </button>
            <div className="landing-hero-google">
              <span className="landing-or-divider">or</span>
              <GoogleLogin
                onSuccess={onGoogleSuccess}
                onError={onGoogleError}
                text="continue_with"
                shape="rectangular"
                theme="filled_black"
                width={240}
              />
            </div>
            {error && <p className="landing-error">{error}</p>}
          </div>
        </div>
        <div className="landing-hero-visual">
          <div className="landing-swipe-demo">
            {cardPosters.length >= 3 ? (
              <>
                <div className="landing-card landing-card-back">
                  <img
                    src={cardPosters[2].poster}
                    alt={cardPosters[2].title}
                    className="landing-card-poster-img"
                  />
                </div>
                <div className="landing-card landing-card-middle">
                  <img
                    src={cardPosters[1].poster}
                    alt={cardPosters[1].title}
                    className="landing-card-poster-img"
                  />
                </div>
                <div className="landing-card landing-card-front">
                  <img
                    src={cardPosters[0].poster}
                    alt={cardPosters[0].title}
                    className="landing-card-poster-img"
                  />
                  <div className="landing-card-overlay">
                    <span className="landing-swipe-hint">👆 Swipe to decide</span>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="landing-card landing-card-back">
                  <div className="landing-card-placeholder"></div>
                </div>
                <div className="landing-card landing-card-middle">
                  <div className="landing-card-placeholder"></div>
                </div>
                <div className="landing-card landing-card-front">
                  <div className="landing-card-placeholder"></div>
                  <div className="landing-card-overlay">
                    <span className="landing-swipe-hint">👆 Swipe to decide</span>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="landing-section landing-how-it-works">
        <h2 className="landing-section-title">How It Works</h2>
        <div className="landing-steps">
          <div className="landing-step">
            <div className="landing-step-number">1</div>
            <div className="landing-step-icon">👥</div>
            <h3 className="landing-step-title">Create a Circle</h3>
            <p className="landing-step-description">
              Invite your partner, roommates, or friends. Everyone swipes independently.
            </p>
          </div>
          <div className="landing-step">
            <div className="landing-step-number">2</div>
            <div className="landing-step-icon">👆</div>
            <h3 className="landing-step-title">Swipe on Movies</h3>
            <p className="landing-step-description">
              Like or pass on movies. Swipe right to like, left to pass. Your votes are private.
            </p>
          </div>
          <div className="landing-step">
            <div className="landing-step-number">3</div>
            <div className="landing-step-icon">🎉</div>
            <h3 className="landing-step-title">Find Your Match</h3>
            <p className="landing-step-description">
              When everyone likes the same movie, it's a match! No more debates or compromises.
            </p>
          </div>
        </div>
      </section>

      {/* Films Section */}
      <section className="landing-section landing-films">
        <h2 className="landing-section-title">Thousands of Films to Choose From</h2>
        <p className="landing-section-subtitle">
          Browse curated collections or discover what's streaming on your favorite services
        </p>

        <div className="landing-films-grid">
          <div className="landing-films-category">
            <h3 className="landing-films-category-title">Streaming Services</h3>
            <div className="landing-films-list">
              <div className="landing-film-tag"><span className="landing-film-icon">🔴</span> Netflix</div>
              <div className="landing-film-tag"><span className="landing-film-icon">📦</span> Prime Video</div>
              <div className="landing-film-tag"><span className="landing-film-icon">💚</span> Hulu</div>
              <div className="landing-film-tag"><span className="landing-film-icon">🏰</span> Disney+</div>
              <div className="landing-film-tag"><span className="landing-film-icon">💜</span> Max</div>
              <div className="landing-film-tag"><span className="landing-film-icon">📚</span> Kanopy</div>
            </div>
          </div>

          <div className="landing-films-category">
            <h3 className="landing-films-category-title">Curated Collections</h3>
            <div className="landing-films-list">
              <div className="landing-film-tag"><span className="landing-film-icon">🎬</span> Top 100 Classics</div>
              <div className="landing-film-tag"><span className="landing-film-icon">🏆</span> Oscar Winners</div>
              <div className="landing-film-tag"><span className="landing-film-icon">🇺🇸</span> AFI Top 100</div>
              <div className="landing-film-tag"><span className="landing-film-icon">🌍</span> Foreign Films</div>
              <div className="landing-film-tag"><span className="landing-film-icon">📼</span> 90s Nostalgia</div>
              <div className="landing-film-tag"><span className="landing-film-icon">🕶️</span> 80s Bangers</div>
            </div>
          </div>

          <div className="landing-films-category landing-films-category-wide">
            <h3 className="landing-films-category-title">Popular Genres</h3>
            <div className="landing-films-list landing-films-list-inline">
              <div className="landing-film-tag"><span className="landing-film-icon">💥</span> Action</div>
              <div className="landing-film-tag"><span className="landing-film-icon">😂</span> Comedy</div>
              <div className="landing-film-tag"><span className="landing-film-icon">👻</span> Horror</div>
              <div className="landing-film-tag"><span className="landing-film-icon">🚀</span> Sci-Fi</div>
              <div className="landing-film-tag"><span className="landing-film-icon">🎥</span> Documentary</div>
            </div>
          </div>
        </div>
      </section>

      {/* Value Props */}
      <section className="landing-section landing-value-props">
        <div className="landing-value-grid">
          <div className="landing-value-card">
            <div className="landing-value-icon">🚫</div>
            <h3 className="landing-value-title">No More "You Pick"</h3>
            <p className="landing-value-description">
              Everyone votes honestly because no one sees your choices until there's a match.
            </p>
          </div>
          <div className="landing-value-card">
            <div className="landing-value-icon">🔒</div>
            <h3 className="landing-value-title">Private Voting</h3>
            <p className="landing-value-description">
              Your swipes stay secret. No judgment, no pressure, no compromising your taste.
            </p>
          </div>
          <div className="landing-value-card">
            <div className="landing-value-icon">💰</div>
            <h3 className="landing-value-title">100% Free</h3>
            <p className="landing-value-description">
              No ads, no premium tier, no catch. Just find movies you all love.
            </p>
          </div>
        </div>
      </section>

      {/* Recently Watched */}
      {recentlyWatched.length > 0 && (
        <section className="landing-section landing-recently-watched">
          <h2 className="landing-section-title">Recently Watched</h2>
          <p className="landing-section-subtitle">
            Real friends matched on these movies you may have missed the first time around — and watched!
          </p>
          <div className="landing-watched-grid">
            {recentlyWatched.slice(0, 6).map((movie, index) => (
              <div key={index} className="landing-watched-card">
                <img
                  src={movie.poster}
                  alt={movie.title}
                  className="landing-watched-poster"
                />
                <div className="landing-watched-info">
                  <span className="landing-watched-title">{movie.title}</span>
                  <span className="landing-watched-year">{movie.year}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Final CTA */}
      <section className="landing-section landing-final-cta">
        <h2 className="landing-final-cta-title">Ready to find your next movie night pick?</h2>
        <button className="landing-btn-primary landing-btn-large" onClick={onGetStarted}>
          Get Started — It's Free
        </button>
        <p className="landing-final-cta-subtitle">Sign up with email or Google in seconds</p>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="landing-footer-links">
          <a href="/privacy">Privacy</a>
          <span className="landing-footer-separator">·</span>
          <a href="/terms">Terms</a>
        </div>
        <p className="landing-footer-copyright">© 2026 Movie Matcher</p>
      </footer>
    </div>
  );
};

export default LandingPage;
