// clients/mobile/components/__tests__/VerdictCard.test.tsx
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { VerdictCard } from '../VerdictCard';

describe('VerdictCard', () => {
  const defaultProps = {
    verdict: 'safe' as const,
    oneLine: 'Test safety message',
    flags: [],
  };

  it('renders with correct testID', () => {
    const { getByTestId } = render(<VerdictCard {...defaultProps} />);
    expect(getByTestId('verdict-card')).toBeTruthy();
  });

  it('displays safe verdict correctly', () => {
    const { getByText } = render(<VerdictCard {...defaultProps} />);
    expect(getByText('✅')).toBeTruthy();
    expect(getByText('No Recalls Found')).toBeTruthy();
    expect(getByText('Test safety message')).toBeTruthy();
  });

  it('displays caution verdict correctly', () => {
    const { getByText } = render(
      <VerdictCard {...defaultProps} verdict="caution" />
    );
    expect(getByText('⚠️')).toBeTruthy();
    expect(getByText('Caution Advised')).toBeTruthy();
  });

  it('displays recall verdict correctly', () => {
    const { getByText } = render(
      <VerdictCard {...defaultProps} verdict="recall" />
    );
    expect(getByText('❌')).toBeTruthy();
    expect(getByText('Recall Alert')).toBeTruthy();
  });

  it('displays avoid verdict correctly', () => {
    const { getByText } = render(
      <VerdictCard {...defaultProps} verdict="avoid" />
    );
    expect(getByText('⛔')).toBeTruthy();
    expect(getByText('Avoid')).toBeTruthy();
  });

  it('shows flags when provided', () => {
    const { getByText } = render(
      <VerdictCard {...defaultProps} flags={['contains_peanuts', 'soft_cheese']} />
    );
    expect(getByText('Flags: contains_peanuts, soft_cheese')).toBeTruthy();
  });

  it('hides flags when empty', () => {
    const { queryByText } = render(<VerdictCard {...defaultProps} flags={[]} />);
    expect(queryByText(/Flags:/)).toBeNull();
  });

  it('renders explain button when onExplain provided', () => {
    const onExplain = jest.fn();
    const { getByTestId } = render(
      <VerdictCard {...defaultProps} onExplain={onExplain} />
    );
    expect(getByTestId('btn-explain')).toBeTruthy();
  });

  it('calls onExplain when explain button pressed', () => {
    const onExplain = jest.fn();
    const { getByTestId } = render(
      <VerdictCard {...defaultProps} onExplain={onExplain} />
    );
    
    fireEvent.press(getByTestId('btn-explain'));
    expect(onExplain).toHaveBeenCalledTimes(1);
  });

  it('renders alert button when onSetAlert provided', () => {
    const onSetAlert = jest.fn();
    const { getByTestId } = render(
      <VerdictCard {...defaultProps} onSetAlert={onSetAlert} />
    );
    expect(getByTestId('btn-alert')).toBeTruthy();
  });

  it('calls onSetAlert when alert button pressed', () => {
    const onSetAlert = jest.fn();
    const { getByTestId } = render(
      <VerdictCard {...defaultProps} onSetAlert={onSetAlert} />
    );
    
    fireEvent.press(getByTestId('btn-alert'));
    expect(onSetAlert).toHaveBeenCalledTimes(1);
  });

  it('does not render buttons when callbacks not provided', () => {
    const { queryByTestId } = render(<VerdictCard {...defaultProps} />);
    expect(queryByTestId('btn-explain')).toBeNull();
    expect(queryByTestId('btn-alert')).toBeNull();
  });
});
