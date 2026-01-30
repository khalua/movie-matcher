import { useEffect, useRef, useCallback, useState } from 'react';

const getApiUrl = () => {
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  if (process.env.NODE_ENV === 'production') {
    return '';
  }
  const API_PORT = process.env.REACT_APP_API_PORT || '5001';
  return `http://${window.location.hostname}:${API_PORT}`;
};

export const useNotifications = (circleId, onNewComment) => {
  const eventSourceRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const onNewCommentRef = useRef(onNewComment);

  // Keep callback ref updated
  useEffect(() => {
    onNewCommentRef.current = onNewComment;
  }, [onNewComment]);

  const connect = useCallback(() => {
    const token = localStorage.getItem('token');
    console.log('useNotifications connect called, circleId:', circleId, 'hasToken:', !!token);
    if (!token || !circleId) {
      console.log('useNotifications: skipping connect - no token or circleId');
      return;
    }

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const apiUrl = getApiUrl();
    const url = `${apiUrl}/api/notifications/stream?token=${encodeURIComponent(token)}&circle_id=${circleId}`;
    console.log('useNotifications: connecting to', url);

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.addEventListener('connected', (e) => {
      console.log('SSE connected:', JSON.parse(e.data));
      setIsConnected(true);
    });

    eventSource.addEventListener('new_comment', (e) => {
      const data = JSON.parse(e.data);
      console.log('New comment notification:', data);
      if (onNewCommentRef.current) {
        onNewCommentRef.current(data);
      }
    });

    eventSource.onerror = (error) => {
      console.error('SSE error:', error, 'readyState:', eventSource.readyState);
      // readyState: 0 = CONNECTING, 1 = OPEN, 2 = CLOSED
      if (eventSource.readyState === 2) {
        // Only reconnect if the connection is actually closed
        setIsConnected(false);
        eventSource.close();

        // Reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting SSE reconnection...');
          connect();
        }, 5000);
      }
    };

    eventSource.onopen = () => {
      console.log('SSE connection opened');
    };
  }, [circleId]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { isConnected, reconnect: connect };
};
