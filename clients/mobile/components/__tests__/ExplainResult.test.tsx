// __tests__/ExplainResult.test.tsx
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Alert } from 'react-native';
import { ExplainResultButton } from '../ExplainResult';

// Mock fetch
global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

// Mock Alert
jest.spyOn(Alert, 'alert').mockImplementation(() => {});

describe('ExplainResultButton', () => {
  const mockProps = {
    baseUrl: 'https://test.api.com',
    scanId: 'test-scan-123',
    onFeedback: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the button correctly', () => {
    const { getByText } = render(<ExplainResultButton {...mockProps} />);
    expect(getByText('Explain This Result (Beta)')).toBeTruthy();
  });

  it('calls API when button is pressed', async () => {
    const mockResponse = {
      summary: 'This product appears safe for babies.',
      reasons: ['No recalls found', 'Approved ingredients'],
      checks: ['Check expiration date'],
      flags: ['baby_safe'],
      disclaimer: 'This is not medical advice.',
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const { getByText } = render(<ExplainResultButton {...mockProps} />);
    
    fireEvent.press(getByText('Explain This Result (Beta)'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        'https://test.api.com/api/v1/chat/explain-result',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scan_id: 'test-scan-123' }),
        }
      );
    });
  });

  it('shows error alert on API failure', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: async () => 'Internal Server Error',
    } as Response);

    const { getByText } = render(<ExplainResultButton {...mockProps} />);
    
    fireEvent.press(getByText('Explain This Result (Beta)'));

    await waitFor(() => {
      expect(Alert.alert).toHaveBeenCalledWith(
        'Explain failed',
        'Internal Server Error'
      );
    });
  });

  it('calls onFeedback when thumbs up is pressed', async () => {
    const mockResponse = {
      summary: 'Test summary',
      reasons: [],
      checks: [],
      flags: [],
      disclaimer: 'Test disclaimer',
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const { getByText } = render(<ExplainResultButton {...mockProps} />);
    
    // Open modal
    fireEvent.press(getByText('Explain This Result (Beta)'));
    
    await waitFor(() => {
      expect(getByText('Test summary')).toBeTruthy();
    });

    // Press thumbs up
    fireEvent.press(getByText('👍 Helpful'));

    expect(mockProps.onFeedback).toHaveBeenCalledWith(true);
  });

  it('calls onFeedback when thumbs down is pressed', async () => {
    const mockResponse = {
      summary: 'Test summary',
      reasons: [],
      checks: [],
      flags: [],
      disclaimer: 'Test disclaimer',
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const { getByText } = render(<ExplainResultButton {...mockProps} />);
    
    // Open modal
    fireEvent.press(getByText('Explain This Result (Beta)'));
    
    await waitFor(() => {
      expect(getByText('Test summary')).toBeTruthy();
    });

    // Press thumbs down
    fireEvent.press(getByText('👎 Not helpful'));

    expect(mockProps.onFeedback).toHaveBeenCalledWith(false);
  });
});
