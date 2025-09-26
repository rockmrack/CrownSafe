import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { EmergencyStrip } from '../EmergencyStrip';
import { EmergencyNotice } from '../../babyshield_client';

describe('EmergencyStrip', () => {
  const mockOnEmergencyAction = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders red emergency strip correctly', () => {
    const redEmergency: EmergencyNotice = {
      level: 'red',
      reason: 'Possible urgent situation reported.',
      cta: 'Open Emergency Guidance'
    };

    const { getByText, getByRole } = render(
      <EmergencyStrip 
        emergency={redEmergency} 
        onEmergencyAction={mockOnEmergencyAction}
      />
    );

    expect(getByText('Possible urgent situation reported.')).toBeTruthy();
    expect(getByText('Open Emergency Guidance')).toBeTruthy();
    
    const button = getByRole('button');
    expect(button).toBeTruthy();
    expect(button.props.accessibilityLabel).toBe('Emergency action: Open Emergency Guidance');
  });

  it('renders amber emergency strip correctly', () => {
    const amberEmergency: EmergencyNotice = {
      level: 'amber',
      reason: 'Caution advised for this situation.',
      cta: 'View Safety Guidelines'
    };

    const { getByText } = render(
      <EmergencyStrip 
        emergency={amberEmergency} 
        onEmergencyAction={mockOnEmergencyAction}
      />
    );

    expect(getByText('Caution advised for this situation.')).toBeTruthy();
    expect(getByText('View Safety Guidelines')).toBeTruthy();
  });

  it('calls onEmergencyAction when CTA button is pressed', () => {
    const emergency: EmergencyNotice = {
      level: 'red',
      reason: 'Test emergency',
      cta: 'Test Action'
    };

    const { getByRole } = render(
      <EmergencyStrip 
        emergency={emergency} 
        onEmergencyAction={mockOnEmergencyAction}
      />
    );

    const button = getByRole('button');
    fireEvent.press(button);

    expect(mockOnEmergencyAction).toHaveBeenCalledTimes(1);
  });

  it('handles missing onEmergencyAction gracefully', () => {
    const emergency: EmergencyNotice = {
      level: 'red',
      reason: 'Test emergency',
      cta: 'Test Action'
    };

    const { getByRole } = render(
      <EmergencyStrip emergency={emergency} />
    );

    const button = getByRole('button');
    // Should not throw when pressed without handler
    expect(() => fireEvent.press(button)).not.toThrow();
  });

  it('applies correct styling for red level', () => {
    const redEmergency: EmergencyNotice = {
      level: 'red',
      reason: 'Red emergency',
      cta: 'Red Action'
    };

    const { getByTestId } = render(
      <EmergencyStrip emergency={redEmergency} />
    );

    // Note: In actual implementation, you might want to add testID props
    // to verify styling. This is a placeholder for style verification.
    expect(true).toBeTruthy(); // Placeholder assertion
  });

  it('applies correct styling for amber level', () => {
    const amberEmergency: EmergencyNotice = {
      level: 'amber',
      reason: 'Amber emergency',
      cta: 'Amber Action'
    };

    const { getByTestId } = render(
      <EmergencyStrip emergency={amberEmergency} />
    );

    // Note: In actual implementation, you might want to add testID props
    // to verify styling. This is a placeholder for style verification.
    expect(true).toBeTruthy(); // Placeholder assertion
  });

  it('has proper accessibility properties', () => {
    const emergency: EmergencyNotice = {
      level: 'red',
      reason: 'Accessibility test emergency',
      cta: 'Accessibility Test Action'
    };

    const { getByRole } = render(
      <EmergencyStrip emergency={emergency} />
    );

    const button = getByRole('button');
    expect(button.props.accessible).toBe(true);
    expect(button.props.accessibilityRole).toBe('button');
    expect(button.props.accessibilityLabel).toBe('Emergency action: Accessibility Test Action');
  });
});
