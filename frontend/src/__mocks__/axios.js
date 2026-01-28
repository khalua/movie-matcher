/**
 * Mock for axios module.
 *
 * Usage in tests:
 * import axios from 'axios';
 * axios.get.mockResolvedValue({ data: { ... } });
 */

const mockAxios = {
  create: jest.fn(() => mockAxios),
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
  },
  defaults: {
    headers: {
      common: {}
    }
  }
};

export default mockAxios;
