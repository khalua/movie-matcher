import React, { useEffect, useState } from 'react';
import './Toast.css';

function Toast({ message, icon, onDismiss, duration = 4000 }) {
  const [isVisible, setIsVisible] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);

  useEffect(() => {
    // Trigger entrance animation
    const showTimer = setTimeout(() => setIsVisible(true), 50);

    // Auto-hide after delay
    const hideTimer = setTimeout(() => {
      handleDismiss();
    }, duration);

    return () => {
      clearTimeout(showTimer);
      clearTimeout(hideTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [duration]);

  const handleDismiss = () => {
    setIsLeaving(true);
    setTimeout(() => {
      onDismiss();
    }, 300);
  };

  return (
    <div
      className={`toast ${isVisible ? 'visible' : ''} ${isLeaving ? 'leaving' : ''}`}
      onClick={handleDismiss}
    >
      {icon && <span className="toast-icon">{icon}</span>}
      <span className="toast-message">{message}</span>
    </div>
  );
}

export default Toast;
