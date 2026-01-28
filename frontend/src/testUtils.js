/**
 * Test utilities for React component testing.
 *
 * Provides helper functions for:
 * - Rendering components with providers (CircleContext, etc.)
 * - Creating mock data
 * - Common test setup
 */
import React from 'react';
import { render } from '@testing-library/react';
import { CircleProvider } from './contexts/CircleContext';

/**
 * Custom render function that wraps components with necessary providers.
 *
 * @param {ReactElement} ui - Component to render
 * @param {Object} options - Render options
 * @param {Object} options.circleValue - Override CircleContext value
 * @returns {Object} - RTL render result
 */
export function renderWithProviders(ui, { circleValue, ...options } = {}) {
  function Wrapper({ children }) {
    return <CircleProvider>{children}</CircleProvider>;
  }

  return render(ui, { wrapper: Wrapper, ...options });
}

/**
 * Create a mock user object
 */
export function createMockUser(overrides = {}) {
  return {
    id: 1,
    email: 'test@example.com',
    display_name: 'Test User',
    is_site_admin: false,
    ...overrides
  };
}

/**
 * Create a mock circle object
 */
export function createMockCircle(overrides = {}) {
  return {
    id: 1,
    name: 'Test Circle',
    member_count: 2,
    role: 'member',
    admin_name: 'Admin User',
    created_at: '2024-01-01T00:00:00Z',
    ...overrides
  };
}

/**
 * Create a mock movie object
 */
export function createMockMovie(overrides = {}) {
  return {
    id: 1,
    title: 'Test Movie',
    year: 2024,
    poster: 'https://example.com/poster.jpg',
    description: 'A test movie description',
    genre: 'Action',
    rating: '8.5',
    length: '120 min',
    starring: 'Test Actor, Another Actor',
    ...overrides
  };
}

/**
 * Create a mock match result
 */
export function createMockMatch(overrides = {}) {
  return {
    ...createMockMovie(),
    match_count: 2,
    matched_users: [
      { id: 1, display_name: 'User One' },
      { id: 2, display_name: 'User Two' }
    ],
    ...overrides
  };
}

/**
 * Mock localStorage for tests
 */
export function mockLocalStorage() {
  const store = {};

  return {
    getItem: jest.fn((key) => store[key] || null),
    setItem: jest.fn((key, value) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      Object.keys(store).forEach((key) => delete store[key]);
    }),
    _store: store
  };
}

/**
 * Wait for async operations in tests
 */
export function waitForAsync() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

/**
 * Setup localStorage mock before each test
 */
export function setupLocalStorageMock() {
  const mockStorage = mockLocalStorage();
  Object.defineProperty(window, 'localStorage', {
    value: mockStorage,
    writable: true
  });
  return mockStorage;
}

// Re-export everything from testing-library for convenience
export * from '@testing-library/react';

// Note: @testing-library/user-event v13 (the version in this project) uses
// direct methods like userEvent.type(), not userEvent.setup().
// For v14+, use: const user = userEvent.setup(); await user.type(...);
// For v13 (current): await userEvent.type(...);
export { default as userEvent } from '@testing-library/user-event';
