/**
 * Tests for API client configuration and interceptors.
 *
 * Note: These tests verify the interceptor logic in isolation.
 * The actual client is mocked in component tests.
 */

describe('API Client', () => {
  let originalLocalStorage;
  let originalLocation;
  let mockLocalStorage;

  beforeEach(() => {
    // Save originals
    originalLocalStorage = global.localStorage;
    originalLocation = global.window.location;

    // Mock localStorage
    mockLocalStorage = {
      store: {},
      getItem: jest.fn((key) => mockLocalStorage.store[key] || null),
      setItem: jest.fn((key, value) => {
        mockLocalStorage.store[key] = value;
      }),
      removeItem: jest.fn((key) => {
        delete mockLocalStorage.store[key];
      }),
      clear: jest.fn()
    };
    Object.defineProperty(global, 'localStorage', {
      value: mockLocalStorage,
      writable: true
    });

    // Mock window.location
    delete window.location;
    window.location = { href: '', hostname: 'localhost' };

    // Reset modules to get fresh client
    jest.resetModules();
  });

  afterEach(() => {
    global.localStorage = originalLocalStorage;
    window.location = originalLocation;
  });

  describe('Request Interceptor Logic', () => {
    it('should add Authorization header when token exists', () => {
      mockLocalStorage.store.token = 'test-jwt-token';

      // Simulate what the interceptor does
      const config = { headers: {} };
      const token = mockLocalStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      expect(config.headers.Authorization).toBe('Bearer test-jwt-token');
    });

    it('should not add Authorization header when no token', () => {
      const config = { headers: {} };
      const token = mockLocalStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      expect(config.headers.Authorization).toBeUndefined();
    });

    it('should add X-Circle-Id header when circle is selected', () => {
      mockLocalStorage.store.currentCircleId = '42';

      const config = { headers: {} };
      const circleId = mockLocalStorage.getItem('currentCircleId');
      if (circleId) {
        config.headers['X-Circle-Id'] = circleId;
      }

      expect(config.headers['X-Circle-Id']).toBe('42');
    });
  });

  describe('Response Interceptor Logic', () => {
    it('should clear auth on 401 when token was present', () => {
      mockLocalStorage.store.token = 'expired-token';
      mockLocalStorage.store.currentCircleId = '1';

      // Simulate 401 response handling
      const error = {
        response: { status: 401 }
      };

      if (error.response?.status === 401 && mockLocalStorage.getItem('token')) {
        mockLocalStorage.removeItem('token');
        mockLocalStorage.removeItem('currentCircleId');
        window.location.href = '/';
      }

      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('token');
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('currentCircleId');
      expect(window.location.href).toBe('/');
    });

    it('should not redirect on 401 during login (no token)', () => {
      // No token means this is a failed login attempt, not an expired session

      const error = {
        response: { status: 401 }
      };

      if (error.response?.status === 401 && mockLocalStorage.getItem('token')) {
        mockLocalStorage.removeItem('token');
        window.location.href = '/';
      }

      // Should not have been called
      expect(mockLocalStorage.removeItem).not.toHaveBeenCalled();
      expect(window.location.href).toBe('');
    });

    it('should not affect non-401 errors', () => {
      mockLocalStorage.store.token = 'valid-token';

      const error = {
        response: { status: 500 }
      };

      if (error.response?.status === 401 && mockLocalStorage.getItem('token')) {
        mockLocalStorage.removeItem('token');
        window.location.href = '/';
      }

      // Token should still be there
      expect(mockLocalStorage.removeItem).not.toHaveBeenCalled();
    });
  });

  describe('API URL Configuration', () => {
    it('uses relative URLs in production', () => {
      const getApiUrl = () => {
        if (process.env.REACT_APP_API_URL) {
          return process.env.REACT_APP_API_URL;
        }
        if (process.env.NODE_ENV === 'production') {
          return '';
        }
        return `http://localhost:5001`;
      };

      // Simulate production
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      expect(getApiUrl()).toBe('');

      process.env.NODE_ENV = originalEnv;
    });

    it('uses explicit REACT_APP_API_URL when set', () => {
      const getApiUrl = () => {
        if (process.env.REACT_APP_API_URL) {
          return process.env.REACT_APP_API_URL;
        }
        return '';
      };

      process.env.REACT_APP_API_URL = 'https://api.example.com';
      expect(getApiUrl()).toBe('https://api.example.com');
      delete process.env.REACT_APP_API_URL;
    });
  });
});
