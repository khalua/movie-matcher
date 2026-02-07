import React from 'react';
import { useNavigate } from 'react-router-dom';
import './SoloBanner.css';

function SoloBanner() {
  const navigate = useNavigate();
  return (
    <div className="solo-banner">
      <div className="solo-banner-content">
        <span className="solo-banner-icon">👋</span>
        <span className="solo-banner-text">
          You're all alone! <button className="solo-banner-link" onClick={() => navigate('/settings')}>Invite others</button> to join this circle.
        </span>
      </div>
    </div>
  );
}

export default SoloBanner;
