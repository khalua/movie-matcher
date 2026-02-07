/**
 * Tests for CircleContext - state management for circles.
 */
import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { CircleProvider, useCircle } from '../../contexts/CircleContext';
import client from '../../api/client';

// Mock the API client
jest.mock('../../api/client');

// Test component that uses the context
function TestConsumer() {
  const { currentCircle, circles, switchCircle, refreshCircles } = useCircle();

  return (
    <div>
      <div data-testid="current-circle">
        {currentCircle ? currentCircle.name : 'none'}
      </div>
      <div data-testid="current-circle-id">
        {currentCircle ? currentCircle.id : 'none'}
      </div>
      <div data-testid="circle-count">{circles.length}</div>
      <button onClick={() => switchCircle(2)}>Switch to Circle 2</button>
      <button onClick={() => switchCircle({ id: 99, name: 'New Circle Object' })}>
        Switch to Object Circle
      </button>
      <button onClick={refreshCircles}>Refresh</button>
      <ul>
        {circles.map((c) => (
          <li key={c.id} data-testid={`circle-${c.id}`}>
            {c.name}
          </li>
        ))}
      </ul>
    </div>
  );
}

describe('CircleContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('useCircle hook', () => {
    it('throws error when used outside provider', () => {
      // Suppress console.error for this test
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        render(<TestConsumer />);
      }).toThrow('useCircle must be used within CircleProvider');

      consoleSpy.mockRestore();
    });
  });

  describe('CircleProvider', () => {
    it('provides initial empty state', () => {
      client.get.mockResolvedValue({ data: [] });

      render(
        <CircleProvider>
          <TestConsumer />
        </CircleProvider>
      );

      expect(screen.getByTestId('current-circle')).toHaveTextContent('none');
      expect(screen.getByTestId('circle-count')).toHaveTextContent('0');
    });

    it('refreshCircles fetches circles from API', async () => {
      const mockCircles = [
        { id: 1, name: 'Circle One' },
        { id: 2, name: 'Circle Two' }
      ];
      client.get.mockResolvedValue({ data: mockCircles });

      render(
        <CircleProvider>
          <TestConsumer />
        </CircleProvider>
      );

      // Click refresh button
      await act(async () => {
        screen.getByText('Refresh').click();
      });

      await waitFor(() => {
        expect(client.get).toHaveBeenCalledWith('/api/circles');
        expect(screen.getByTestId('circle-count')).toHaveTextContent('2');
      });
    });

    it('sets first circle as default when no saved circle', async () => {
      const mockCircles = [
        { id: 1, name: 'First Circle' },
        { id: 2, name: 'Second Circle' }
      ];
      client.get.mockResolvedValue({ data: mockCircles });

      render(
        <CircleProvider>
          <TestConsumer />
        </CircleProvider>
      );

      await act(async () => {
        screen.getByText('Refresh').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('current-circle')).toHaveTextContent('First Circle');
      });
    });

    it('restores saved circle from localStorage', async () => {
      localStorage.setItem('currentCircleId', '2');

      const mockCircles = [
        { id: 1, name: 'First Circle' },
        { id: 2, name: 'Saved Circle' }
      ];
      client.get.mockResolvedValue({ data: mockCircles });

      render(
        <CircleProvider>
          <TestConsumer />
        </CircleProvider>
      );

      await act(async () => {
        screen.getByText('Refresh').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('current-circle')).toHaveTextContent('Saved Circle');
      });
    });

    it('falls back to first circle when saved circle not found', async () => {
      localStorage.setItem('currentCircleId', '999'); // Non-existent

      const mockCircles = [
        { id: 1, name: 'Fallback Circle' },
        { id: 2, name: 'Other Circle' }
      ];
      client.get.mockResolvedValue({ data: mockCircles });

      render(
        <CircleProvider>
          <TestConsumer />
        </CircleProvider>
      );

      await act(async () => {
        screen.getByText('Refresh').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('current-circle')).toHaveTextContent('Fallback Circle');
      });
    });

    it('switchCircle changes current circle and saves to localStorage', async () => {
      const mockCircles = [
        { id: 1, name: 'Circle One' },
        { id: 2, name: 'Circle Two' }
      ];
      client.get.mockResolvedValue({ data: mockCircles });

      render(
        <CircleProvider>
          <TestConsumer />
        </CircleProvider>
      );

      await act(async () => {
        screen.getByText('Refresh').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('current-circle')).toHaveTextContent('Circle One');
      });

      // Switch to circle 2
      await act(async () => {
        screen.getByText('Switch to Circle 2').click();
      });

      expect(screen.getByTestId('current-circle')).toHaveTextContent('Circle Two');
      expect(localStorage.getItem('currentCircleId')).toBe('2');
    });

    it('switchCircle does nothing for invalid circle id', async () => {
      const mockCircles = [{ id: 1, name: 'Only Circle' }];
      client.get.mockResolvedValue({ data: mockCircles });

      render(
        <CircleProvider>
          <TestConsumer />
        </CircleProvider>
      );

      await act(async () => {
        screen.getByText('Refresh').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('current-circle')).toHaveTextContent('Only Circle');
      });

      // Try to switch to non-existent circle
      await act(async () => {
        screen.getByText('Switch to Circle 2').click();
      });

      // Should still be on the original circle
      expect(screen.getByTestId('current-circle')).toHaveTextContent('Only Circle');
    });

    it('handles API errors gracefully', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      client.get.mockRejectedValue(new Error('Network error'));

      render(
        <CircleProvider>
          <TestConsumer />
        </CircleProvider>
      );

      await act(async () => {
        screen.getByText('Refresh').click();
      });

      // Should not crash, circles remain empty
      await waitFor(() => {
        expect(screen.getByTestId('circle-count')).toHaveTextContent('0');
      });

      consoleSpy.mockRestore();
    });

    it('switchCircle accepts a circle object directly (not just an ID)', async () => {
      const mockCircles = [{ id: 1, name: 'Existing Circle' }];
      client.get.mockResolvedValue({ data: mockCircles });

      render(
        <CircleProvider>
          <TestConsumer />
        </CircleProvider>
      );

      await act(async () => {
        screen.getByText('Refresh').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('current-circle')).toHaveTextContent('Existing Circle');
      });

      // Switch using a circle object (not in the circles array)
      await act(async () => {
        screen.getByText('Switch to Object Circle').click();
      });

      expect(screen.getByTestId('current-circle')).toHaveTextContent('New Circle Object');
      expect(screen.getByTestId('current-circle-id')).toHaveTextContent('99');
      expect(localStorage.getItem('currentCircleId')).toBe('99');
    });

    it('switchCircle with object works even when circles array is empty', async () => {
      client.get.mockResolvedValue({ data: [] });

      render(
        <CircleProvider>
          <TestConsumer />
        </CircleProvider>
      );

      // Circles are empty, currentCircle is null
      expect(screen.getByTestId('current-circle')).toHaveTextContent('none');

      // Switch using object - should work despite empty circles list
      await act(async () => {
        screen.getByText('Switch to Object Circle').click();
      });

      expect(screen.getByTestId('current-circle')).toHaveTextContent('New Circle Object');
      expect(localStorage.getItem('currentCircleId')).toBe('99');
    });
  });
});
