/**
 * Mock for the API client (frontend/src/api/client.js).
 *
 * This mock is used when testing components that import the client.
 *
 * Usage in tests:
 * jest.mock('../api/client');
 * import client from '../api/client';
 * client.get.mockResolvedValue({ data: [...] });
 */

const mockClient = {
  get: jest.fn(() => Promise.resolve({ data: {} })),
  post: jest.fn(() => Promise.resolve({ data: {} })),
  put: jest.fn(() => Promise.resolve({ data: {} })),
  delete: jest.fn(() => Promise.resolve({ data: {} })),
  interceptors: {
    request: {
      use: jest.fn(),
      eject: jest.fn()
    },
    response: {
      use: jest.fn(),
      eject: jest.fn()
    }
  }
};

export default mockClient;
