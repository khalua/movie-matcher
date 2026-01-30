import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import { useCircle } from './CircleContext';
import { useNotifications } from '../hooks/useNotifications';

const NotificationContext = createContext();

export const NotificationProvider = ({ children }) => {
  const { currentCircle } = useCircle();
  const [unreadCommentsCount, setUnreadCommentsCount] = useState(0);
  const [lastComment, setLastComment] = useState(null);
  const commentListenersRef = useRef([]);

  const handleNewComment = useCallback((data) => {
    // Increment unread count when a new comment arrives
    setUnreadCommentsCount(prev => prev + 1);
    // Store the last comment for subscribers
    setLastComment(data);
    // Notify all listeners
    commentListenersRef.current.forEach(listener => listener(data));
  }, []);

  const { isConnected } = useNotifications(
    currentCircle?.id,
    handleNewComment
  );

  const markCommentsRead = useCallback(() => {
    setUnreadCommentsCount(0);
  }, []);

  const setInitialUnreadCount = useCallback((count) => {
    setUnreadCommentsCount(count);
  }, []);

  // Subscribe to new comment events
  const subscribeToComments = useCallback((listener) => {
    commentListenersRef.current.push(listener);
    // Return unsubscribe function
    return () => {
      commentListenersRef.current = commentListenersRef.current.filter(l => l !== listener);
    };
  }, []);

  return (
    <NotificationContext.Provider value={{
      unreadCommentsCount,
      setUnreadCommentsCount: setInitialUnreadCount,
      markCommentsRead,
      isConnected,
      lastComment,
      subscribeToComments
    }}>
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotificationContext = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotificationContext must be used within NotificationProvider');
  }
  return context;
};
