import React from 'react';
import './SoloBanner.css';

function SoloBanner({ onInviteClick }) {
  return (
    <div className="solo-banner">
      <div className="solo-banner-content">
        <span className="solo-banner-icon">👋</span>
        <span className="solo-banner-text">
          You're all alone! <button className="solo-banner-link" onClick={onInviteClick}>Invite others</button> to join this circle.
        </span>
      </div>
    </div>
  );
}

export default SoloBanner;
