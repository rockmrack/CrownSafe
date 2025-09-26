// clients/mobile/components/__tests__/ChatBox.test.tsx
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Alert } from 'react-native';
import { ChatBox } from '../ChatBox';

// Mock fetch
global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

// Mock Alert
jest.spyOn(Alert, 'alert').mockImplementation(() => {});

describe('ChatBox', () => {
  const mockProps = {
    apiBase: 'https://test.api.com',
    scanId: 'test-scan-123',
    smartChips: ['Pregnancy risk?', 'Allergies?', 'Alternatives?'],
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders emergency strip and smart chips', () => {
    const { getByText } = render(<ChatBox {...mockProps} />);
    
    expect(getByText('Emergency Guidance')).toBeTruthy();
    expect(getByText('Pregnancy risk?')).toBeTruthy();
    expect(getByText('Allergies?')).toBeTruthy();
    expect(getByText('Alternatives?')).toBeTruthy();
  });

  it('renders text input and send button', () => {
    const { getByPlaceholderText, getByText } = render(<ChatBox {...mockProps} />);
    
    expect(getByPlaceholderText('Ask a question about this product…')).toBeTruthy();
    expect(getByText('Send')).toBeTruthy();
  });

  it('sends message when text is entered and send is pressed', async () => {
    const mockResponse = {
      conversation_id: 'conv-123',
      intent: 'pregnancy_risk',
      message: {
        summary: 'This product appears safe during pregnancy.',
        reasons: ['No harmful ingredients found'],
        checks: ['Check expiration date'],
        flags: ['pregnancy_safe'],
        disclaimer: 'This is not medical advice.',
      },
      trace_id: 'trace-123',
      tool_calls: [],
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const { getByPlaceholderText, getByText } = render(<ChatBox {...mockProps} />);
    
    const textInput = getByPlaceholderText('Ask a question about this product…');
    const sendButton = getByText('Send');
    
    fireEvent.changeText(textInput, 'Is this safe during pregnancy?');
    fireEvent.press(sendButton);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        'https://test.api.com/api/v1/chat/conversation',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scan_id: 'test-scan-123',
            user_query: 'Is this safe during pregnancy?',
            conversation_id: undefined,
          }),
        }
      );
    });
  });

  it('handles smart chip press', async () => {
    const mockResponse = {
      conversation_id: 'conv-123',
      intent: 'allergy_question',
      message: {
        summary: 'This product contains common allergens.',
        reasons: ['Contains milk and soy'],
        checks: ['Check allergen warnings'],
        flags: ['contains_milk', 'contains_soy'],
        disclaimer: 'This is not medical advice.',
      },
      trace_id: 'trace-123',
      tool_calls: [],
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const { getByText } = render(<ChatBox {...mockProps} />);
    
    fireEvent.press(getByText('Allergies?'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        'https://test.api.com/api/v1/chat/conversation',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scan_id: 'test-scan-123',
            user_query: 'Allergies?',
            conversation_id: undefined,
          }),
        }
      );
    });
  });

  it('displays error alert on API failure', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: async () => 'Internal Server Error',
    } as Response);

    const { getByPlaceholderText, getByText } = render(<ChatBox {...mockProps} />);
    
    const textInput = getByPlaceholderText('Ask a question about this product…');
    const sendButton = getByText('Send');
    
    fireEvent.changeText(textInput, 'Test question');
    fireEvent.press(sendButton);

    await waitFor(() => {
      expect(Alert.alert).toHaveBeenCalledWith(
        'Chat error',
        'Internal Server Error'
      );
    });
  });

  it('disables send button when text is empty', () => {
    const { getByText } = render(<ChatBox {...mockProps} />);
    
    const sendButton = getByText('Send');
    expect(sendButton.props.accessibilityState?.disabled).toBe(true);
  });

  it('enables send button when text is entered', () => {
    const { getByPlaceholderText, getByText } = render(<ChatBox {...mockProps} />);
    
    const textInput = getByPlaceholderText('Ask a question about this product…');
    const sendButton = getByText('Send');
    
    fireEvent.changeText(textInput, 'Test question');
    
    expect(sendButton.props.accessibilityState?.disabled).toBe(false);
  });

  it('shows thinking indicator when busy', async () => {
    // Mock a slow response
    mockFetch.mockImplementationOnce(() => 
      new Promise(resolve => setTimeout(() => resolve({
        ok: true,
        json: async () => ({
          conversation_id: 'conv-123',
          intent: 'unclear_intent',
          message: {
            summary: 'Test response',
            reasons: [],
            checks: [],
            flags: [],
            disclaimer: 'Test disclaimer',
          },
          trace_id: 'trace-123',
          tool_calls: [],
        }),
      } as Response), 100))
    );

    const { getByPlaceholderText, getByText, queryByText } = render(<ChatBox {...mockProps} />);
    
    const textInput = getByPlaceholderText('Ask a question about this product…');
    const sendButton = getByText('Send');
    
    fireEvent.changeText(textInput, 'Test question');
    fireEvent.press(sendButton);

    // Should show thinking indicator
    expect(queryByText('Thinking…')).toBeTruthy();

    await waitFor(() => {
      expect(queryByText('Thinking…')).toBeNull();
    });
  });
});
