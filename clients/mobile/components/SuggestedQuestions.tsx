import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';

interface SuggestedQuestionsProps {
  questions: string[];
  onQuestionSelect?: (question: string) => void;
  maxItems?: number;
}

export const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({
  questions,
  onQuestionSelect,
  maxItems = 3,
}) => {
  if (!questions || questions.length === 0) {
    return null;
  }

  const displayQuestions = questions.slice(0, maxItems);

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Suggested questions:</Text>
      
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {displayQuestions.map((question, index) => (
          <TouchableOpacity
            key={index}
            style={styles.questionChip}
            onPress={() => onQuestionSelect?.(question)}
            accessible={true}
            accessibilityRole="button"
            accessibilityLabel={`Ask: ${question}`}
          >
            <Text style={styles.questionText}>{question}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginTop: 12,
    marginBottom: 8,
  },
  label: {
    fontSize: 13,
    color: '#6B7280', // Gray-500
    fontWeight: '500',
    marginBottom: 8,
  },
  scrollContent: {
    paddingHorizontal: 4,
  },
  questionChip: {
    backgroundColor: '#F3F4F6', // Gray-100
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginRight: 8,
    borderWidth: 1,
    borderColor: '#E5E7EB', // Gray-200
    minHeight: 36,
    justifyContent: 'center',
    // Shadow for iOS
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.05,
    shadowRadius: 1,
    // Elevation for Android
    elevation: 1,
  },
  questionText: {
    fontSize: 13,
    color: '#374151', // Gray-700
    fontWeight: '500',
    textAlign: 'center',
  },
});

export default SuggestedQuestions;
