import { createContext, useState, useContext, useEffect, useCallback } from 'react';
import client from '../api/client';

const CircleContext = createContext();

export const CircleProvider = ({ children }) => {
  const [currentCircle, setCurrentCircle] = useState(null);
  const [circles, setCircles] = useState([]);

  const refreshCircles = useCallback(async () => {
    try {
      const response = await client.get('/api/circles');
      setCircles(response.data);
    } catch (error) {
      console.error('Error refreshing circles:', error);
    }
  }, []);

  useEffect(() => {
    if (circles.length === 0) return;

    // Load current circle from localStorage
    const savedCircleId = localStorage.getItem('currentCircleId');
    if (savedCircleId) {
      const circle = circles.find(c => c.id === parseInt(savedCircleId));
      if (circle) {
        setCurrentCircle(circle);
        return;
      }
    }

    // Default to first circle if no saved circle or saved circle not found
    setCurrentCircle(prev => {
      if (prev) return prev;
      localStorage.setItem('currentCircleId', circles[0].id);
      return circles[0];
    });
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
      switchCircle,
      refreshCircles
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
