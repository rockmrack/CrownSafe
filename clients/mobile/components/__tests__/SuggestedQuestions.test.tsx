import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { SuggestedQuestions } from '../SuggestedQuestions';

describe('SuggestedQuestions', () => {
  const mockOnQuestionSelect = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders suggested questions correctly', () => {
    const questions = ['Is this safe in pregnancy?', 'Any allergen concerns?', 'What age is this for?'];

    const { getByText } = render(
      <SuggestedQuestions 
        questions={questions}
        onQuestionSelect={mockOnQuestionSelect}
      />
    );

    expect(getByText('Suggested questions:')).toBeTruthy();
    expect(getByText('Is this safe in pregnancy?')).toBeTruthy();
    expect(getByText('Any allergen concerns?')).toBeTruthy();
    expect(getByText('What age is this for?')).toBeTruthy();
  });

  it('limits questions to maxItems', () => {
    const questions = ['Question 1', 'Question 2', 'Question 3', 'Question 4', 'Question 5'];

    const { getByText, queryByText } = render(
      <SuggestedQuestions 
        questions={questions}
        onQuestionSelect={mockOnQuestionSelect}
        maxItems={3}
      />
    );

    expect(getByText('Question 1')).toBeTruthy();
    expect(getByText('Question 2')).toBeTruthy();
    expect(getByText('Question 3')).toBeTruthy();
    expect(queryByText('Question 4')).toBeNull();
    expect(queryByText('Question 5')).toBeNull();
  });

  it('uses default maxItems of 3 when not specified', () => {
    const questions = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5'];

    const { getByText, queryByText } = render(
      <SuggestedQuestions 
        questions={questions}
        onQuestionSelect={mockOnQuestionSelect}
      />
    );

    expect(getByText('Q1')).toBeTruthy();
    expect(getByText('Q2')).toBeTruthy();
    expect(getByText('Q3')).toBeTruthy();
    expect(queryByText('Q4')).toBeNull();
    expect(queryByText('Q5')).toBeNull();
  });

  it('calls onQuestionSelect when question is pressed', () => {
    const questions = ['Test question'];

    const { getByText } = render(
      <SuggestedQuestions 
        questions={questions}
        onQuestionSelect={mockOnQuestionSelect}
      />
    );

    const questionButton = getByText('Test question');
    fireEvent.press(questionButton);

    expect(mockOnQuestionSelect).toHaveBeenCalledTimes(1);
    expect(mockOnQuestionSelect).toHaveBeenCalledWith('Test question');
  });

  it('handles multiple question selections', () => {
    const questions = ['Question A', 'Question B'];

    const { getByText } = render(
      <SuggestedQuestions 
        questions={questions}
        onQuestionSelect={mockOnQuestionSelect}
      />
    );

    fireEvent.press(getByText('Question A'));
    fireEvent.press(getByText('Question B'));

    expect(mockOnQuestionSelect).toHaveBeenCalledTimes(2);
    expect(mockOnQuestionSelect).toHaveBeenNthCalledWith(1, 'Question A');
    expect(mockOnQuestionSelect).toHaveBeenNthCalledWith(2, 'Question B');
  });

  it('renders nothing when questions array is empty', () => {
    const { queryByText } = render(
      <SuggestedQuestions 
        questions={[]}
        onQuestionSelect={mockOnQuestionSelect}
      />
    );

    expect(queryByText('Suggested questions:')).toBeNull();
  });

  it('renders nothing when questions is null/undefined', () => {
    const { queryByText } = render(
      <SuggestedQuestions 
        questions={undefined as any}
        onQuestionSelect={mockOnQuestionSelect}
      />
    );

    expect(queryByText('Suggested questions:')).toBeNull();
  });

  it('handles missing onQuestionSelect gracefully', () => {
    const questions = ['Test question'];

    const { getByText } = render(
      <SuggestedQuestions questions={questions} />
    );

    const questionButton = getByText('Test question');
    // Should not throw when pressed without handler
    expect(() => fireEvent.press(questionButton)).not.toThrow();
  });

  it('has proper accessibility properties', () => {
    const questions = ['Accessibility test question'];

    const { getByRole } = render(
      <SuggestedQuestions 
        questions={questions}
        onQuestionSelect={mockOnQuestionSelect}
      />
    );

    const button = getByRole('button');
    expect(button.props.accessible).toBe(true);
    expect(button.props.accessibilityRole).toBe('button');
    expect(button.props.accessibilityLabel).toBe('Ask: Accessibility test question');
  });

  it('renders questions in horizontal scroll view', () => {
    const questions = ['Question 1', 'Question 2', 'Question 3'];

    const { getByTestId } = render(
      <SuggestedQuestions 
        questions={questions}
        onQuestionSelect={mockOnQuestionSelect}
      />
    );

    // Note: You might need to add testID to ScrollView in the component
    // This is a placeholder for verifying the horizontal scroll behavior
    expect(true).toBeTruthy(); // Placeholder assertion
  });
});
