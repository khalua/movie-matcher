/**
 * Tests for PackSelector component.
 *
 * Covers:
 * - Rendering when currentCircle is null (e.g., during account creation)
 * - Fetching packs when circle is available
 * - Category filtering
 * - Error handling
 */
import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PackSelector from '../../components/PackSelector';
import client from '../../api/client';

jest.mock('../../api/client');

// Variable to control what useCircle returns per test
let mockCircleValue = { currentCircle: null };

jest.mock('../../contexts/CircleContext', () => ({
  useCircle: () => mockCircleValue
}));

describe('PackSelector', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockCircleValue = { currentCircle: null };
  });

  describe('when currentCircle is null', () => {
    it('does not crash and shows loading state', () => {
      render(<PackSelector embedded={true} />);

      expect(screen.getByText('Loading movie packs...')).toBeInTheDocument();
    });

    it('does not call the packs API', () => {
      render(<PackSelector embedded={true} />);

      expect(client.get).not.toHaveBeenCalled();
    });
  });

  describe('when currentCircle is available', () => {
    const mockCircle = { id: 42, name: 'Test Circle' };
    const mockPacks = [
      { id: 1, name: 'Netflix Hits', icon: '🎬', description: 'Top Netflix movies', category: 'streaming', movie_count: 50 },
      { id: 2, name: 'Horror Classics', icon: '👻', description: 'Scary movies', category: 'genre', movie_count: 30 }
    ];

    beforeEach(() => {
      mockCircleValue = { currentCircle: mockCircle };
    });

    it('fetches packs with circle_id', async () => {
      client.get.mockResolvedValueOnce({ data: { packs: mockPacks } });

      await act(async () => {
        render(<PackSelector embedded={true} />);
      });

      await waitFor(() => {
        expect(client.get).toHaveBeenCalledWith('/api/packs?circle_id=42');
      });
    });

    it('renders pack cards after loading', async () => {
      client.get.mockResolvedValueOnce({ data: { packs: mockPacks } });

      await act(async () => {
        render(<PackSelector embedded={true} />);
      });

      await waitFor(() => {
        expect(screen.getByText('Netflix Hits')).toBeInTheDocument();
        expect(screen.getByText('Horror Classics')).toBeInTheDocument();
      });
    });

    it('shows error message when API fails', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      client.get.mockRejectedValueOnce(new Error('Network error'));

      await act(async () => {
        render(<PackSelector embedded={true} />);
      });

      await waitFor(() => {
        expect(screen.getByText('Failed to load movie packs')).toBeInTheDocument();
      });

      consoleSpy.mockRestore();
    });

    it('filters packs by category', async () => {
      client.get.mockResolvedValueOnce({ data: { packs: mockPacks } });

      await act(async () => {
        render(<PackSelector embedded={true} />);
      });

      await waitFor(() => {
        expect(screen.getByText('Netflix Hits')).toBeInTheDocument();
      });

      // Click "Streaming" category
      await act(async () => {
        screen.getByText('Streaming').click();
      });

      expect(screen.getByText('Netflix Hits')).toBeInTheDocument();
      expect(screen.queryByText('Horror Classics')).not.toBeInTheDocument();
    });
  });

  describe('when currentCircle changes from null to a circle', () => {
    it('fetches packs once circle becomes available', async () => {
      const mockPacks = [
        { id: 1, name: 'Action Pack', icon: '💥', description: 'Action movies', category: 'genre', movie_count: 25 }
      ];
      client.get.mockResolvedValue({ data: { packs: mockPacks } });

      // Start with null circle
      mockCircleValue = { currentCircle: null };
      const { rerender } = render(<PackSelector embedded={true} />);

      // Should not have fetched
      expect(client.get).not.toHaveBeenCalled();

      // Simulate circle becoming available
      mockCircleValue = { currentCircle: { id: 7, name: 'New Circle' } };
      await act(async () => {
        rerender(<PackSelector embedded={true} />);
      });

      await waitFor(() => {
        expect(client.get).toHaveBeenCalledWith('/api/packs?circle_id=7');
        expect(screen.getByText('Action Pack')).toBeInTheDocument();
      });
    });
  });

  describe('circle movie count', () => {
    const mockCircle = { id: 42, name: 'Test Circle' };
    const mockPacks = [
      { id: 1, name: 'Netflix Hits', icon: '🎬', description: 'Top Netflix movies', category: 'streaming', movie_count: 50 }
    ];

    beforeEach(() => {
      mockCircleValue = { currentCircle: mockCircle };
    });

    it('displays circle movie count when returned by API', async () => {
      client.get.mockResolvedValueOnce({
        data: { packs: mockPacks, circle_movie_count: 142 }
      });

      await act(async () => {
        render(<PackSelector embedded={true} />);
      });

      await waitFor(() => {
        expect(screen.getByText('142 movies in circle')).toBeInTheDocument();
      });
    });

    it('shows singular "movie" for count of 1', async () => {
      client.get.mockResolvedValueOnce({
        data: { packs: mockPacks, circle_movie_count: 1 }
      });

      await act(async () => {
        render(<PackSelector embedded={true} />);
      });

      await waitFor(() => {
        expect(screen.getByText('1 movie in circle')).toBeInTheDocument();
      });
    });

    it('displays 0 movies for empty circle', async () => {
      client.get.mockResolvedValueOnce({
        data: { packs: mockPacks, circle_movie_count: 0 }
      });

      await act(async () => {
        render(<PackSelector embedded={true} />);
      });

      await waitFor(() => {
        expect(screen.getByText('0 movies in circle')).toBeInTheDocument();
      });
    });

    it('does not display count when API does not return it', async () => {
      client.get.mockResolvedValueOnce({
        data: { packs: mockPacks }
      });

      await act(async () => {
        render(<PackSelector embedded={true} />);
      });

      await waitFor(() => {
        expect(screen.getByText('Netflix Hits')).toBeInTheDocument();
      });

      expect(screen.queryByText(/movies in circle/)).not.toBeInTheDocument();
    });
  });
});
