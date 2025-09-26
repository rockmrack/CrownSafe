import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import { AlternativeItem } from '../babyshield_client';

interface AlternativesListProps {
  alternatives: AlternativeItem[];
  scanId: string;
  onAlternativeClick?: (scanId: string, altId: string) => void;
  maxItems?: number;
}

export const AlternativesList: React.FC<AlternativesListProps> = ({
  alternatives,
  scanId,
  onAlternativeClick,
  maxItems = 3,
}) => {
  if (!alternatives || alternatives.length === 0) {
    return null;
  }

  const displayItems = alternatives.slice(0, maxItems);

  const handleAlternativePress = (altId: string) => {
    onAlternativeClick?.(scanId, altId);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Safer Alternatives</Text>
      <Text style={styles.subtitle}>Consider these options instead:</Text>
      
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {displayItems.map((item, index) => (
          <TouchableOpacity
            key={item.id}
            style={styles.alternativeCard}
            onPress={() => handleAlternativePress(item.id)}
            accessible={true}
            accessibilityLabel={`Safer alternative: ${item.name}. Reason: ${item.reason}`}
            accessibilityRole="button"
          >
            <View style={styles.cardContent}>
              <Text style={styles.itemName}>
                {item.name}
                {item.brand && <Text style={styles.brand}> by {item.brand}</Text>}
              </Text>
              
              <Text style={styles.reason}>
                <Text style={styles.reasonLabel}>Why: </Text>
                {item.reason}
              </Text>
              
              {item.tags && item.tags.length > 0 && (
                <View style={styles.tagsContainer}>
                  {item.tags.slice(0, 3).map((tag, tagIndex) => (
                    <View key={tagIndex} style={styles.tag}>
                      <Text style={styles.tagText}>{tag}</Text>
                    </View>
                  ))}
                </View>
              )}
              
              {/* Safety indicators */}
              <View style={styles.indicatorsContainer}>
                {item.pregnancy_safe === true && (
                  <View style={[styles.indicator, styles.pregnancyIndicator]}>
                    <Text style={styles.indicatorText}>Pregnancy Safe</Text>
                  </View>
                )}
                
                {item.allergy_safe_for && item.allergy_safe_for.length > 0 && (
                  <View style={[styles.indicator, styles.allergyIndicator]}>
                    <Text style={styles.indicatorText}>
                      {item.allergy_safe_for.length === 1 
                        ? `${item.allergy_safe_for[0]}-free` 
                        : `Allergy-safe`}
                    </Text>
                  </View>
                )}
                
                {item.age_min_months !== undefined && (
                  <View style={[styles.indicator, styles.ageIndicator]}>
                    <Text style={styles.indicatorText}>
                      {item.age_min_months === 0 ? 'Newborn+' : `${item.age_min_months}m+`}
                    </Text>
                  </View>
                )}
              </View>
            </View>
            
            <View style={styles.arrow}>
              <Text style={styles.arrowText}>→</Text>
            </View>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2D3748',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: '#718096',
    marginBottom: 12,
  },
  scrollView: {
    maxHeight: 300, // Limit height for better UX
  },
  alternativeCard: {
    backgroundColor: '#F7FAFC',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    flexDirection: 'row',
    alignItems: 'center',
    // Shadow for iOS
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    // Elevation for Android
    elevation: 1,
  },
  cardContent: {
    flex: 1,
  },
  itemName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2D3748',
    marginBottom: 6,
  },
  brand: {
    fontWeight: '400',
    color: '#4A5568',
  },
  reason: {
    fontSize: 14,
    color: '#4A5568',
    lineHeight: 20,
    marginBottom: 8,
  },
  reasonLabel: {
    fontWeight: '500',
    color: '#2D3748',
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 8,
  },
  tag: {
    backgroundColor: '#EDF2F7',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    marginRight: 6,
    marginBottom: 4,
  },
  tagText: {
    fontSize: 12,
    color: '#4A5568',
    fontWeight: '500',
  },
  indicatorsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  indicator: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    marginRight: 6,
    marginBottom: 4,
  },
  pregnancyIndicator: {
    backgroundColor: '#C6F6D5',
  },
  allergyIndicator: {
    backgroundColor: '#BEE3F8',
  },
  ageIndicator: {
    backgroundColor: '#FED7D7',
  },
  indicatorText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#2D3748',
  },
  arrow: {
    marginLeft: 12,
  },
  arrowText: {
    fontSize: 18,
    color: '#A0AEC0',
  },
});

export default AlternativesList;
