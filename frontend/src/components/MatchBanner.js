import React, { useEffect, useState } from 'react';
import './MatchBanner.css';

function MatchBanner({ match, onDismiss, autoHide = true, autoHideDelay = 5000 }) {
  const [isVisible, setIsVisible] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);

  useEffect(() => {
    // Trigger entrance animation
    const showTimer = setTimeout(() => setIsVisible(true), 50);

    // Auto-hide after delay if enabled
    let hideTimer;
    if (autoHide && autoHideDelay > 0) {
      hideTimer = setTimeout(() => {
        handleDismiss();
      }, autoHideDelay);
    }

    return () => {
      clearTimeout(showTimer);
      if (hideTimer) clearTimeout(hideTimer);
    };
  }, [autoHide, autoHideDelay]);

  const handleDismiss = () => {
    setIsLeaving(true);
    setTimeout(() => {
      onDismiss();
    }, 300); // Match exit animation duration
  };

  if (!match) return null;

  const isFullMatch = match.match_type === 'full';
  const movie = match.movie;

  return (
    <div
      className={`match-banner ${isVisible ? 'visible' : ''} ${isLeaving ? 'leaving' : ''} ${isFullMatch ? 'full-match' : 'partial-match'}`}
      onClick={handleDismiss}
    >
      {isFullMatch && <div className="confetti-container">
        {[...Array(20)].map((_, i) => (
          <div key={i} className="confetti" style={{
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 0.5}s`,
            backgroundColor: ['#ff6b6b', '#4ecdc4', '#ffe66d', '#95e1d3', '#f38181'][i % 5]
          }} />
        ))}
      </div>}

      <div className="match-content">
        <div className="match-icon">
          {isFullMatch ? '🎉' : '✨'}
        </div>
        <div className="match-text">
          <h3>{isFullMatch ? 'Full Match!' : 'Match!'}</h3>
          <p className="movie-title">{movie?.title}</p>
          <p className="match-details">
            {isFullMatch
              ? `Everyone in the circle wants to watch this!`
              : `${match.like_count} of ${match.member_count} members like this movie`
            }
          </p>
        </div>
      </div>
    </div>
  );
}

export default MatchBanner;
