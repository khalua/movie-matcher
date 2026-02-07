import React, { useState, useEffect, useRef, useCallback } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import client from '../api/client';
import './LandingPage.css';

// Static posters for the hero card stack - cached locally in /public/posters/
const HERO_POSTERS = [
  { title: 'The Godfather', poster: '/posters/godfather.jpg' },
  { title: 'Pulp Fiction', poster: '/posters/pulp-fiction.jpg' },
  { title: 'The Shawshank Redemption', poster: '/posters/shawshank-redemption.jpg' },
  { title: 'Inception', poster: '/posters/inception.jpg' },
  { title: 'The Dark Knight', poster: '/posters/dark-knight.jpg' },
  { title: 'Fight Club', poster: '/posters/fight-club.jpg' },
];

const LandingPage = ({
  onGetStarted,
  onSignIn,
  onGoogleSuccess,
  onGoogleError,
  error
}) => {
  const [recentlyWatched, setRecentlyWatched] = useState([]);
  const [cardIndex, setCardIndex] = useState(0);
  const [swipeState, setSwipeState] = useState({ x: 0, dragging: false, swiping: null });
  const dragRef = useRef(null);
  const startRef = useRef({ x: 0, y: 0 });

  const getVisibleCards = useCallback(() => {
    const cards = [];
    for (let i = 0; i < 3; i++) {
      const idx = (cardIndex + i) % HERO_POSTERS.length;
      cards.push({ ...HERO_POSTERS[idx], stackIndex: i });
    }
    return cards;
  }, [cardIndex]);

  const triggerSwipe = useCallback((direction) => {
    const xTarget = direction === 'right' ? 400 : -400;
    setSwipeState({ x: xTarget, dragging: false, swiping: direction });
    setTimeout(() => {
      setCardIndex((prev) => (prev + 1) % HERO_POSTERS.length);
      setSwipeState({ x: 0, dragging: false, swiping: null });
    }, 350);
  }, []);

  // Auto-swipe every 3 seconds when idle
  useEffect(() => {
    if (swipeState.dragging || swipeState.swiping) return;
    const timer = setTimeout(() => {
      triggerSwipe(Math.random() > 0.3 ? 'right' : 'left');
    }, 3000);
    return () => clearTimeout(timer);
  }, [cardIndex, swipeState.dragging, swipeState.swiping, triggerSwipe]);

  const handlePointerDown = (e) => {
    if (swipeState.swiping) return;
    startRef.current = { x: e.clientX, y: e.clientY };
    dragRef.current = true;
    setSwipeState({ x: 0, dragging: true, swiping: null });
  };

  const handlePointerMove = (e) => {
    if (!dragRef.current) return;
    const dx = e.clientX - startRef.current.x;
    setSwipeState({ x: dx, dragging: true, swiping: null });
  };

  const handlePointerUp = () => {
    if (!dragRef.current) return;
    dragRef.current = false;
    const dx = swipeState.x;
    if (Math.abs(dx) > 60) {
      triggerSwipe(dx > 0 ? 'right' : 'left');
    } else {
      setSwipeState({ x: 0, dragging: false, swiping: null });
    }
  };

  useEffect(() => {
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

    fetchRecentlyWatched();
  }, []);

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
            <span className="landing-hero-title-brand">Movie Matcher</span>
            End Movie Night<br />Arguments. Forever.
          </h1>
          <p className="landing-hero-subtitle">
            Swipe on movies you love. When everyone in your group matches, you've found your next watch party.
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
            {getVisibleCards().reverse().map((movie) => {
              const isFront = movie.stackIndex === 0;
              const rotation = movie.stackIndex === 0 ? 5 : movie.stackIndex === 1 ? -8 : -18;
              const scale = movie.stackIndex === 0 ? 1 : movie.stackIndex === 1 ? 0.94 : 0.88;
              const xOffset = movie.stackIndex === 0 ? -40 : movie.stackIndex === 1 ? -70 : -95;
              const opacity = movie.stackIndex === 0 ? 1 : movie.stackIndex === 1 ? 0.9 : 0.75;

              let style;
              if (isFront) {
                const dragX = swipeState.x;
                const dragRotation = 5 + dragX * 0.15;
                style = {
                  transform: `translateX(calc(-40% + ${dragX}px)) rotate(${dragRotation}deg)`,
                  opacity: 1,
                  zIndex: 3,
                  transition: swipeState.dragging ? 'none' : 'all 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
                  cursor: 'grab',
                  border: '2px solid var(--color-accent)',
                };
              } else {
                style = {
                  transform: `translateX(${xOffset}%) rotate(${rotation}deg) scale(${scale})`,
                  opacity,
                  zIndex: 3 - movie.stackIndex,
                  transition: 'all 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
                };
              }

              return (
                <div
                  key={`${movie.title}-${cardIndex}-${movie.stackIndex}`}
                  className="landing-card"
                  style={{ ...style, left: '50%', top: 0 }}
                  onPointerDown={isFront ? handlePointerDown : undefined}
                  onPointerMove={isFront ? handlePointerMove : undefined}
                  onPointerUp={isFront ? handlePointerUp : undefined}
                  onPointerLeave={isFront ? handlePointerUp : undefined}
                >
                  <img
                    src={movie.poster}
                    alt={movie.title}
                    className="landing-card-poster-img"
                    draggable={false}
                  />
                  {isFront && Math.abs(swipeState.x) > 20 && (
                    <div className={`landing-swipe-badge ${swipeState.x > 0 ? 'landing-swipe-like' : 'landing-swipe-nope'}`}>
                      {swipeState.x > 0 ? 'LIKE' : 'NOPE'}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          <div className="landing-swipe-buttons">
            <button
              className="landing-swipe-btn landing-swipe-btn-nope"
              onClick={() => triggerSwipe('left')}
              aria-label="Pass"
            >
              ✕
            </button>
            <button
              className="landing-swipe-btn landing-swipe-btn-like"
              onClick={() => triggerSwipe('right')}
              aria-label="Like"
            >
              ♥
            </button>
          </div>
          <span className="landing-swipe-hint">Swipe or tap to decide</span>
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
            What friend groups are watching and loving right now
          </p>
          <div className="landing-watched-grid">
            {recentlyWatched.slice(0, 5).map((movie, index) => (
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
            <a
              href="https://youtu.be/-pXaMlXzn9I"
              target="_blank"
              rel="noopener noreferrer"
              className="landing-watched-card landing-watched-card-link"
              key="mr-wiggins"
            >
              <img
                src="/MrWigginsPoster.jpg"
                alt="Mr. Wiggins"
                className="landing-watched-poster"
              />
              <div className="landing-watched-info">
                <span className="landing-watched-title">Mr. Wiggins</span>
                <span className="landing-watched-year">2025</span>
              </div>
            </a>
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
