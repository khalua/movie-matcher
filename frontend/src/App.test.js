/**
 * Tests for main App component.
 *
 * Tests cover:
 * - Landing page (initial state when not authenticated)
 * - Login flow (after clicking Sign In from landing page)
 * - Registration flow (after clicking Get Started from landing page)
 * - API calls on form submission
 *
 * Note: More complex integration tests should be done with E2E testing.
 * These unit tests focus on isolated component behavior.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';
import client from './api/client';

// Mock the API client
jest.mock('./api/client');

// Mock Google OAuth
jest.mock('@react-oauth/google', () => ({
  GoogleOAuthProvider: ({ children }) => <div>{children}</div>,
  GoogleLogin: () => <button data-testid="google-login">Sign in with Google</button>
}));

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
    setCircles: jest.fn(),
    circleMembers: [],
    newMember: null,
    clearNewMember: jest.fn()
  })
}));

describe('App', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    client.get.mockResolvedValue({ data: [] });
    client.post.mockResolvedValue({ data: {} });
  });

  describe('Landing page', () => {
    it('renders landing page when no token', () => {
      render(<MemoryRouter><App /></MemoryRouter>);

      // Landing page should show hero content
      expect(screen.getByText(/End Movie Night/i)).toBeInTheDocument();
      expect(screen.getByText(/Arguments. Forever./i)).toBeInTheDocument();
    });

    it('shows Sign In and Get Started buttons', () => {
      render(<MemoryRouter><App /></MemoryRouter>);

      // Header buttons
      expect(screen.getByRole('button', { name: /^Sign In$/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^Get Started$/i })).toBeInTheDocument();
    });

    it('navigates to login form when Sign In is clicked', () => {
      render(<MemoryRouter><App /></MemoryRouter>);

      fireEvent.click(screen.getByRole('button', { name: /^Sign In$/i }));

      // Now login form should be visible
      expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^Sign In$/i })).toBeInTheDocument();
    });

    it('navigates to registration form when Get Started is clicked', () => {
      render(<MemoryRouter><App /></MemoryRouter>);

      fireEvent.click(screen.getByRole('button', { name: /^Get Started$/i }));

      // Now registration form should be visible with Name field
      expect(screen.getByPlaceholderText('What should we call you?')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument();
    });
  });

  describe('Login flow', () => {
    const navigateToLoginForm = () => {
      render(<MemoryRouter><App /></MemoryRouter>);
      fireEvent.click(screen.getByRole('button', { name: /^Sign In$/i }));
    };

    it('calls login API on form submission', async () => {
      client.post.mockResolvedValueOnce({
        data: {
          access_token: 'test-jwt-token',
          user: { id: 1, email: 'test@example.com', display_name: 'Test' },
          circles: [{ id: 1, name: 'My Circle' }]
        }
      });

      navigateToLoginForm();

      fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
        target: { value: 'test@example.com' }
      });
      fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
        target: { value: 'password123' }
      });
      fireEvent.click(screen.getByRole('button', { name: /^Sign In$/i }));

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

      navigateToLoginForm();

      fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
        target: { value: 'test@example.com' }
      });
      fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
        target: { value: 'wrongpassword' }
      });
      fireEvent.click(screen.getByRole('button', { name: /^Sign In$/i }));

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

      navigateToLoginForm();

      fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
        target: { value: 'test@example.com' }
      });
      fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
        target: { value: 'password123' }
      });
      fireEvent.click(screen.getByRole('button', { name: /^Sign In$/i }));

      await waitFor(() => {
        expect(localStorage.getItem('token')).toBe('test-jwt-token');
      });
    });

    it('shows link to switch to registration', () => {
      navigateToLoginForm();

      expect(screen.getByText(/Create account/i)).toBeInTheDocument();
    });
  });

  describe('Registration flow', () => {
    const navigateToRegistrationForm = () => {
      render(<MemoryRouter><App /></MemoryRouter>);
      fireEvent.click(screen.getByRole('button', { name: /^Get Started$/i }));
    };

    it('calls register API on form submission', async () => {
      client.post.mockResolvedValueOnce({
        data: {
          access_token: 'test-jwt-token',
          user: { id: 1, email: 'new@example.com', display_name: 'New User' },
          circles: []
        }
      });

      navigateToRegistrationForm();

      fireEvent.change(screen.getByPlaceholderText('What should we call you?'), {
        target: { value: 'New User' }
      });
      fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
        target: { value: 'new@example.com' }
      });
      fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
        target: { value: 'password123' }
      });
      fireEvent.click(screen.getByRole('button', { name: /Create Account/i }));

      await waitFor(() => {
        expect(client.post).toHaveBeenCalledWith('/api/auth/register', {
          email: 'new@example.com',
          password: 'password123',
          display_name: 'New User'
        });
      });
    });

    it('shows link to switch to login', () => {
      navigateToRegistrationForm();

      expect(screen.getByText(/Have an account\?/i)).toBeInTheDocument();
      // Use link-button class to distinguish from other Sign in buttons
      const authToggle = screen.getByText(/Have an account\?/i).closest('p');
      expect(authToggle.querySelector('button')).toHaveTextContent(/Sign in/i);
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

      render(<MemoryRouter><App /></MemoryRouter>);

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

      render(<MemoryRouter><App /></MemoryRouter>);

      await waitFor(() => {
        expect(client.get).toHaveBeenCalledWith('/api/circles');
      });
    });
  });
});
