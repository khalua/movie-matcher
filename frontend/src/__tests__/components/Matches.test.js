/**
 * Tests for Matches component.
 *
 * Covers:
 * - Solo user (< 2 members) stops loading and shows no-matches message
 * - Multiple users auto-fetches matches
 * - Displays matched movies
 * - Handles API errors
 */
import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import Matches from '../../Matches';
import client from '../../api/client';

jest.mock('../../api/client');

let mockCircleValue = { currentCircle: { id: 1, name: 'Test Circle' } };

jest.mock('../../contexts/CircleContext', () => ({
  useCircle: () => mockCircleValue
}));

describe('Matches', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockCircleValue = { currentCircle: { id: 1, name: 'Test Circle' } };
  });

  describe('solo user (fewer than 2 members)', () => {
    it('stops loading and shows no-matches message', async () => {
      const soloUser = [{ id: 10, display_name: 'Lonely User' }];
      client.get.mockResolvedValueOnce({ data: soloUser });

      await act(async () => {
        render(<Matches />);
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      expect(screen.getByText('No matches found between the selected users.')).toBeInTheDocument();
    });

    it('does not call the matches API', async () => {
      const soloUser = [{ id: 10, display_name: 'Lonely User' }];
      client.get.mockResolvedValueOnce({ data: soloUser });

      await act(async () => {
        render(<Matches />);
      });

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      expect(client.post).not.toHaveBeenCalled();
    });
  });

  describe('multiple users', () => {
    const twoUsers = [
      { id: 1, display_name: 'Alice' },
      { id: 2, display_name: 'Bob' }
    ];

    it('auto-fetches matches when 2+ users exist', async () => {
      client.get.mockResolvedValueOnce({ data: twoUsers });
      client.post.mockResolvedValueOnce({ data: [] });

      await act(async () => {
        render(<Matches />);
      });

      await waitFor(() => {
        expect(client.post).toHaveBeenCalledWith('/api/movies/matches', {
          userIds: [1, 2]
        });
      });
    });

    it('displays matched movies', async () => {
      const matchedMovies = [
        {
          id: 100,
          title: 'The Godfather',
          year: 1972,
          poster: 'http://example.com/poster.jpg',
          description: 'A crime saga',
          genre: 'Crime',
          rating: '9.2',
          length: '175 min',
          starring: 'Marlon Brando',
          matched_users: [
            { id: 1, display_name: 'Alice' },
            { id: 2, display_name: 'Bob' }
          ],
          comment_count: 0,
          unread_comment_count: 0
        }
      ];

      client.get.mockResolvedValueOnce({ data: twoUsers });
      client.post.mockResolvedValueOnce({ data: matchedMovies });
      // Streaming availability call
      client.get.mockResolvedValueOnce({ data: { streaming: [] } });

      await act(async () => {
        render(<Matches />);
      });

      await waitFor(() => {
        expect(screen.getByText('The Godfather')).toBeInTheDocument();
      });
    });

    it('shows no-matches message when no movies match', async () => {
      client.get.mockResolvedValueOnce({ data: twoUsers });
      client.post.mockResolvedValueOnce({ data: [] });

      await act(async () => {
        render(<Matches />);
      });

      await waitFor(() => {
        expect(screen.getByText('No matches found between the selected users.')).toBeInTheDocument();
      });
    });
  });

  describe('error handling', () => {
    it('shows error when fetching users fails', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      client.get.mockRejectedValueOnce(new Error('Network error'));

      await act(async () => {
        render(<Matches />);
      });

      await waitFor(() => {
        expect(screen.getByText('Failed to fetch users. Please try again.')).toBeInTheDocument();
      });

      consoleSpy.mockRestore();
    });
  });
});
