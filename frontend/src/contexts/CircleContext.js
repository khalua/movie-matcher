import { createContext, useState, useContext, useEffect, useCallback, useRef } from 'react';
import client from '../api/client';

const CircleContext = createContext();

export const CircleProvider = ({ children }) => {
  const [currentCircle, setCurrentCircle] = useState(null);
  const [circles, setCircles] = useState([]);
  const [circleMembers, setCircleMembers] = useState([]);
  const [newMember, setNewMember] = useState(null);
  const previousMemberIdsRef = useRef(null);

  const refreshCircles = useCallback(async () => {
    try {
      const response = await client.get('/api/circles');
      setCircles(response.data);
    } catch (error) {
      console.error('Error refreshing circles:', error);
    }
  }, []);

  const fetchCircleMembers = useCallback(async (circleId) => {
    // Don't fetch if no circleId or no auth token
    if (!circleId || !localStorage.getItem('token')) return;
    try {
      const response = await client.get(`/api/circles/${circleId}/members`);
      const members = response.data;

      // Check for new members (only if we had previous data)
      if (previousMemberIdsRef.current !== null) {
        const previousIds = previousMemberIdsRef.current;
        const newMembers = members.filter(m => !previousIds.has(m.id));

        if (newMembers.length > 0) {
          // Show toast for the first new member
          setNewMember(newMembers[0]);
        }
      }

      // Update the previous member IDs reference
      previousMemberIdsRef.current = new Set(members.map(m => m.id));
      setCircleMembers(members);
    } catch (error) {
      console.error('Error fetching circle members:', error);
    }
  }, []);

  const clearNewMember = useCallback(() => {
    setNewMember(null);
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

  // Fetch members when current circle changes
  useEffect(() => {
    if (currentCircle?.id) {
      // Reset previous member IDs when switching circles
      previousMemberIdsRef.current = null;
      fetchCircleMembers(currentCircle.id);
    }
  }, [currentCircle?.id, fetchCircleMembers]);

  // Poll for new members every 30 seconds
  useEffect(() => {
    if (!currentCircle?.id) return;

    const interval = setInterval(() => {
      fetchCircleMembers(currentCircle.id);
    }, 30000);

    return () => clearInterval(interval);
  }, [currentCircle?.id, fetchCircleMembers]);

  const switchCircle = (circleId) => {
    const circle = circles.find(c => c.id === circleId);
    if (circle) {
      // Reset member tracking when switching circles
      previousMemberIdsRef.current = null;
      setCircleMembers([]);
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
      refreshCircles,
      circleMembers,
      fetchCircleMembers,
      newMember,
      clearNewMember
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
