import React, { createContext, useState, useContext, useEffect } from 'react';

const CircleContext = createContext();

export const CircleProvider = ({ children }) => {
  const [currentCircle, setCurrentCircle] = useState(null);
  const [circles, setCircles] = useState([]);

  useEffect(() => {
    // Load current circle from localStorage
    const savedCircleId = localStorage.getItem('currentCircleId');
    if (savedCircleId && circles.length > 0) {
      const circle = circles.find(c => c.id === parseInt(savedCircleId));
      if (circle) {
        setCurrentCircle(circle);
      } else if (circles.length > 0) {
        // If saved circle not found, default to first
        setCurrentCircle(circles[0]);
        localStorage.setItem('currentCircleId', circles[0].id);
      }
    } else if (circles.length > 0 && !currentCircle) {
      // Default to first circle
      setCurrentCircle(circles[0]);
      localStorage.setItem('currentCircleId', circles[0].id);
    }
  }, [circles]);

  const switchCircle = (circleId) => {
    const circle = circles.find(c => c.id === circleId);
    if (circle) {
      setCurrentCircle(circle);
      localStorage.setItem('currentCircleId', circleId);
    }
  };

  return (
    <CircleContext.Provider value={{
      currentCircle,
      circles,
      setCircles,
      switchCircle
    }}>
      {children}
    </CircleContext.Provider>
  );
};

export const useCircle = () => {
  const context = useContext(CircleContext);
  if (!context) {
    throw new Error('useCircle must be used within CircleProvider');
  }
  return context;
};
