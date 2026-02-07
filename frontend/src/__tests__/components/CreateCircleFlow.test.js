/**
 * Tests for CreateCircleFlow component.
 *
 * Covers:
 * - Circle creation step
 * - Pack selector receives isAdmin=true so packs can be added
 * - Pack addition flow and continue button state
 * - Invite step after packs
 */
import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CreateCircleFlow from '../../components/CreateCircleFlow';
import client from '../../api/client';

jest.mock('../../api/client');

let mockCircleValue = {
  circles: [],
  setCircles: jest.fn(),
  switchCircle: jest.fn(),
  currentCircle: null
};

jest.mock('../../contexts/CircleContext', () => ({
  useCircle: () => mockCircleValue
}));

// Mock PackSelector to inspect props and simulate adding packs
let capturedPackSelectorProps = {};
jest.mock('../../components/PackSelector', () => {
  return function MockPackSelector(props) {
    capturedPackSelectorProps = props;
    return (
      <div data-testid="pack-selector">
        <span data-testid="is-admin">{String(props.isAdmin)}</span>
        <span data-testid="embedded">{String(props.embedded)}</span>
        <button
          data-testid="simulate-add-pack"
          onClick={() => props.onPackAdded && props.onPackAdded({ added_count: 25 })}
        >
          Add Pack
        </button>
      </div>
    );
  };
});

describe('CreateCircleFlow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    capturedPackSelectorProps = {};
    mockCircleValue = {
      circles: [],
      setCircles: jest.fn(),
      switchCircle: jest.fn(),
      currentCircle: null
    };
  });

  it('creates a circle and moves to packs step', async () => {
    const newCircle = { id: 5, name: 'House' };
    client.post.mockResolvedValueOnce({ data: newCircle });

    render(<CreateCircleFlow onComplete={jest.fn()} />);

    await userEvent.type(screen.getByPlaceholderText(/e.g.,/), 'House');
    await userEvent.click(screen.getByText('Create Circle'));

    await waitFor(() => {
      expect(client.post).toHaveBeenCalledWith('/api/circles', { name: 'House' });
      expect(screen.getByText('Add Movies to House')).toBeInTheDocument();
    });
  });

  it('passes isAdmin=true and embedded=true to PackSelector', async () => {
    const newCircle = { id: 5, name: 'House' };
    client.post.mockResolvedValueOnce({ data: newCircle });

    render(<CreateCircleFlow onComplete={jest.fn()} />);

    await userEvent.type(screen.getByPlaceholderText(/e.g.,/), 'House');
    await userEvent.click(screen.getByText('Create Circle'));

    await waitFor(() => {
      expect(screen.getByTestId('pack-selector')).toBeInTheDocument();
    });

    expect(screen.getByTestId('is-admin')).toHaveTextContent('true');
    expect(screen.getByTestId('embedded')).toHaveTextContent('true');
  });

  it('disables continue button until a pack is added', async () => {
    const newCircle = { id: 5, name: 'House' };
    client.post.mockResolvedValueOnce({ data: newCircle });

    render(<CreateCircleFlow onComplete={jest.fn()} />);

    await userEvent.type(screen.getByPlaceholderText(/e.g.,/), 'House');
    await userEvent.click(screen.getByText('Create Circle'));

    await waitFor(() => {
      expect(screen.getByTestId('pack-selector')).toBeInTheDocument();
    });

    // Continue button should be disabled with helper text
    const continueBtn = screen.getByText('Add movies to continue');
    expect(continueBtn).toBeDisabled();
    expect(screen.getByText('Add at least one movie pack to get started')).toBeInTheDocument();
  });

  it('enables continue button after adding a pack', async () => {
    const newCircle = { id: 5, name: 'House' };
    client.post.mockResolvedValueOnce({ data: newCircle });

    render(<CreateCircleFlow onComplete={jest.fn()} />);

    await userEvent.type(screen.getByPlaceholderText(/e.g.,/), 'House');
    await userEvent.click(screen.getByText('Create Circle'));

    await waitFor(() => {
      expect(screen.getByTestId('pack-selector')).toBeInTheDocument();
    });

    // Simulate adding a pack
    await userEvent.click(screen.getByTestId('simulate-add-pack'));

    await waitFor(() => {
      expect(screen.getByText('25 movies added')).toBeInTheDocument();
    });

    expect(screen.getByText('Continue')).not.toBeDisabled();
  });

  it('moves to invite step after clicking continue', async () => {
    const newCircle = { id: 5, name: 'House' };
    client.post.mockResolvedValueOnce({ data: newCircle });

    render(<CreateCircleFlow onComplete={jest.fn()} />);

    await userEvent.type(screen.getByPlaceholderText(/e.g.,/), 'House');
    await userEvent.click(screen.getByText('Create Circle'));

    await waitFor(() => {
      expect(screen.getByTestId('pack-selector')).toBeInTheDocument();
    });

    // Add a pack then continue
    await userEvent.click(screen.getByTestId('simulate-add-pack'));

    client.post.mockResolvedValueOnce({
      data: { email_body: 'Join my circle at https://example.com/invite/abc123' }
    });

    await userEvent.click(screen.getByText('Continue'));

    await waitFor(() => {
      expect(screen.getByText("You're all set!")).toBeInTheDocument();
    });
  });
});
