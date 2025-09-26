// clients/mobile/screens/__tests__/PrivacySettingsScreen.test.tsx
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Alert } from 'react-native';
import { PrivacySettingsScreen } from '../PrivacySettingsScreen';
import * as chatProfileAPI from '../../api/chatProfile';

// Mock the API
jest.mock('../../api/chatProfile');
const mockGetProfile = chatProfileAPI.getProfile as jest.MockedFunction<typeof chatProfileAPI.getProfile>;
const mockPutProfile = chatProfileAPI.putProfile as jest.MockedFunction<typeof chatProfileAPI.putProfile>;

// Mock Alert
jest.spyOn(Alert, 'alert').mockImplementation(() => {});

describe('PrivacySettingsScreen', () => {
  const mockProps = {
    apiBase: 'https://test.api.com',
    authToken: 'test-token',
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    mockGetProfile.mockImplementation(() => new Promise(() => {})); // Never resolves

    const { getByTestId } = render(<PrivacySettingsScreen {...mockProps} />);
    
    expect(getByTestId('activity-indicator')).toBeTruthy();
  });

  it('loads and displays profile data', async () => {
    const mockProfile = {
      consent_personalization: true,
      memory_paused: false,
      allergies: ['peanuts', 'milk'],
      pregnancy_trimester: 2,
      pregnancy_due_date: '2025-06-15',
      child_birthdate: null,
    };

    mockGetProfile.mockResolvedValueOnce(mockProfile);

    const { getByText, getByDisplayValue } = render(<PrivacySettingsScreen {...mockProps} />);

    await waitFor(() => {
      expect(getByText('Personalization & Data')).toBeTruthy();
      expect(getByDisplayValue('peanuts, milk')).toBeTruthy();
      expect(getByDisplayValue('2')).toBeTruthy();
      expect(getByDisplayValue('2025-06-15')).toBeTruthy();
    });
  });

  it('handles profile loading error gracefully', async () => {
    mockGetProfile.mockRejectedValueOnce(new Error('Network error'));

    render(<PrivacySettingsScreen {...mockProps} />);

    await waitFor(() => {
      expect(Alert.alert).toHaveBeenCalledWith(
        'Profile',
        'Network error'
      );
    });
  });

  it('handles 401 error gracefully', async () => {
    mockGetProfile.mockRejectedValueOnce(new Error('HTTP 401'));

    render(<PrivacySettingsScreen {...mockProps} />);

    await waitFor(() => {
      expect(Alert.alert).toHaveBeenCalledWith(
        'Profile',
        'HTTP 401'
      );
    });
  });

  it('updates allergies when text input changes', async () => {
    const mockProfile = {
      consent_personalization: false,
      memory_paused: false,
      allergies: [],
      pregnancy_trimester: null,
      pregnancy_due_date: null,
      child_birthdate: null,
    };

    mockGetProfile.mockResolvedValueOnce(mockProfile);

    const { getByPlaceholderText } = render(<PrivacySettingsScreen {...mockProps} />);

    await waitFor(() => {
      const allergiesInput = getByPlaceholderText('e.g., peanuts, dairy, soy');
      fireEvent.changeText(allergiesInput, 'peanuts, dairy');
      
      expect(allergiesInput.props.value).toBe('peanuts, dairy');
    });
  });

  it('updates pregnancy trimester when valid number is entered', async () => {
    const mockProfile = {
      consent_personalization: false,
      memory_paused: false,
      allergies: [],
      pregnancy_trimester: null,
      pregnancy_due_date: null,
      child_birthdate: null,
    };

    mockGetProfile.mockResolvedValueOnce(mockProfile);

    const { getByPlaceholderText } = render(<PrivacySettingsScreen {...mockProps} />);

    await waitFor(() => {
      const trimesterInput = getByPlaceholderText('1, 2, or 3');
      fireEvent.changeText(trimesterInput, '2');
      
      expect(trimesterInput.props.value).toBe('2');
    });
  });

  it('rejects invalid pregnancy trimester values', async () => {
    const mockProfile = {
      consent_personalization: false,
      memory_paused: false,
      allergies: [],
      pregnancy_trimester: null,
      pregnancy_due_date: null,
      child_birthdate: null,
    };

    mockGetProfile.mockResolvedValueOnce(mockProfile);

    const { getByPlaceholderText } = render(<PrivacySettingsScreen {...mockProps} />);

    await waitFor(() => {
      const trimesterInput = getByPlaceholderText('1, 2, or 3');
      
      // Test invalid values
      fireEvent.changeText(trimesterInput, '4');
      expect(trimesterInput.props.value).toBe('');
      
      fireEvent.changeText(trimesterInput, '0');
      expect(trimesterInput.props.value).toBe('');
      
      fireEvent.changeText(trimesterInput, 'invalid');
      expect(trimesterInput.props.value).toBe('');
    });
  });

  it('saves profile successfully', async () => {
    const mockProfile = {
      consent_personalization: true,
      memory_paused: false,
      allergies: ['peanuts'],
      pregnancy_trimester: 1,
      pregnancy_due_date: '2025-06-15',
      child_birthdate: null,
    };

    mockGetProfile.mockResolvedValueOnce(mockProfile);
    mockPutProfile.mockResolvedValueOnce({
      ok: true,
      updated_at: '2025-09-24T20:30:00Z',
    });

    const { getByText } = render(<PrivacySettingsScreen {...mockProps} />);

    await waitFor(() => {
      const saveButton = getByText('Save');
      fireEvent.press(saveButton);
    });

    await waitFor(() => {
      expect(mockPutProfile).toHaveBeenCalledWith(
        'https://test.api.com',
        mockProfile,
        'test-token'
      );
      expect(Alert.alert).toHaveBeenCalledWith(
        'Saved',
        'Your preferences have been updated.'
      );
    });
  });

  it('handles save error', async () => {
    const mockProfile = {
      consent_personalization: false,
      memory_paused: false,
      allergies: [],
      pregnancy_trimester: null,
      pregnancy_due_date: null,
      child_birthdate: null,
    };

    mockGetProfile.mockResolvedValueOnce(mockProfile);
    mockPutProfile.mockRejectedValueOnce(new Error('Save failed'));

    const { getByText } = render(<PrivacySettingsScreen {...mockProps} />);

    await waitFor(() => {
      const saveButton = getByText('Save');
      fireEvent.press(saveButton);
    });

    await waitFor(() => {
      expect(Alert.alert).toHaveBeenCalledWith(
        'Save failed',
        'Save failed'
      );
    });
  });

  it('shows erase history confirmation', async () => {
    const mockProfile = {
      consent_personalization: false,
      memory_paused: false,
      allergies: [],
      pregnancy_trimester: null,
      pregnancy_due_date: null,
      child_birthdate: null,
    };

    mockGetProfile.mockResolvedValueOnce(mockProfile);

    const { getByText } = render(<PrivacySettingsScreen {...mockProps} />);

    await waitFor(() => {
      const eraseButton = getByText('Erase history');
      fireEvent.press(eraseButton);
    });

    expect(Alert.alert).toHaveBeenCalledWith(
      'Erase conversation history',
      'This will delete your saved chat messages. You\'ll keep access to the app.',
      expect.arrayContaining([
        expect.objectContaining({ text: 'Cancel', style: 'cancel' }),
        expect.objectContaining({ text: 'OK' }),
      ])
    );
  });
});
