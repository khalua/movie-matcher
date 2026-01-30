/**
 * Tests for main App component.
 *
 * Tests cover:
 * - Initial render (login form when not authenticated)
 * - Basic form interactions
 * - API calls on form submission
 *
 * Note: More complex integration tests should be done with E2E testing.
 * These unit tests focus on isolated component behavior.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';
import client from './api/client';

// Mock the API client
jest.mock('./api/client');

// Mock child components to isolate App testing
jest.mock('./MovieSwiper', () => {
  return function MockMovieSwiper() {
    return <div data-testid="movie-swiper">MovieSwiper</div>;
  };
});

jest.mock('./Matches', () => {
  return function MockMatches() {
    return <div data-testid="matches">Matches</div>;
  };
});

jest.mock('./contexts/CircleContext', () => ({
  CircleProvider: ({ children }) => <div>{children}</div>,
  useCircle: () => ({
    currentCircle: { id: 1, name: 'Test Circle' },
    circles: [{ id: 1, name: 'Test Circle' }],
    switchCircle: jest.fn(),
    refreshCircles: jest.fn(),
    setCircles: jest.fn()
  })
}));

jest.mock('./contexts/NotificationContext', () => ({
  NotificationProvider: ({ children }) => <div>{children}</div>,
  useNotificationContext: () => ({
    unreadCommentsCount: 0,
    setUnreadCommentsCount: jest.fn(),
    markCommentsRead: jest.fn(),
    isConnected: false
  })
}));

describe('App', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    client.get.mockResolvedValue({ data: [] });
    client.post.mockResolvedValue({ data: {} });
  });

  describe('Unauthenticated state', () => {
    it('renders login form when no token', () => {
      render(<App />);

      // Use actual placeholder text from App.js
      expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    it('shows register link', () => {
      render(<App />);

      // The "Create account" text should be present
      expect(screen.getByText(/create account/i)).toBeInTheDocument();
    });
  });

  describe('Login flow', () => {
    it('calls login API on form submission', async () => {
      client.post.mockResolvedValueOnce({
        data: {
          access_token: 'test-jwt-token',
          user: { id: 1, email: 'test@example.com', display_name: 'Test' },
          circles: [{ id: 1, name: 'My Circle' }]
        }
      });

      render(<App />);

      fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
        target: { value: 'test@example.com' }
      });
      fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
        target: { value: 'password123' }
      });
      fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(client.post).toHaveBeenCalledWith('/api/auth/login', {
          email: 'test@example.com',
          password: 'password123'
        });
      });
    });

    it('displays error on failed login', async () => {
      client.post.mockRejectedValueOnce({
        response: { data: { error: 'Invalid credentials' } }
      });

      render(<App />);

      fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
        target: { value: 'test@example.com' }
      });
      fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
        target: { value: 'wrongpassword' }
      });
      fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
      });
    });

    it('stores token in localStorage on successful login', async () => {
      client.post.mockResolvedValueOnce({
        data: {
          access_token: 'test-jwt-token',
          user: { id: 1, email: 'test@example.com', display_name: 'Test' },
          circles: [{ id: 1, name: 'My Circle' }]
        }
      });

      render(<App />);

      fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
        target: { value: 'test@example.com' }
      });
      fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
        target: { value: 'password123' }
      });
      fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(localStorage.getItem('token')).toBe('test-jwt-token');
      });
    });
  });

  describe('Authenticated state', () => {
    it('fetches user profile on mount when token exists', async () => {
      // Set token BEFORE render
      localStorage.setItem('token', 'valid-token');

      client.get.mockImplementation((url) => {
        if (url === '/api/auth/profile') {
          return Promise.resolve({
            data: {
              id: 1,
              email: 'test@example.com',
              display_name: 'Test'
            }
          });
        }
        if (url === '/api/circles') {
          return Promise.resolve({
            data: [{ id: 1, name: 'Test Circle' }]
          });
        }
        return Promise.resolve({ data: [] });
      });

      render(<App />);

      await waitFor(() => {
        expect(client.get).toHaveBeenCalledWith('/api/auth/profile');
      });
    });

    it('fetches circles on mount when token exists', async () => {
      // Set token BEFORE render
      localStorage.setItem('token', 'valid-token');

      client.get.mockImplementation((url) => {
        if (url === '/api/auth/profile') {
          return Promise.resolve({
            data: {
              id: 1,
              email: 'test@example.com',
              display_name: 'Test'
            }
          });
        }
        if (url === '/api/circles') {
          return Promise.resolve({
            data: [{ id: 1, name: 'Test Circle' }]
          });
        }
        return Promise.resolve({ data: [] });
      });

      render(<App />);

      await waitFor(() => {
        expect(client.get).toHaveBeenCalledWith('/api/circles');
      });
    });
  });
});
