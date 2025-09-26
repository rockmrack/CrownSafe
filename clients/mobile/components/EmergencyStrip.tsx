import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { EmergencyNotice } from '../babyshield_client';

interface EmergencyStripProps {
  emergency: EmergencyNotice;
  onEmergencyAction?: () => void;
  jurisdictionCode?: string | null;
}

export const EmergencyStrip: React.FC<EmergencyStripProps> = ({
  emergency,
  onEmergencyAction,
  jurisdictionCode,
}) => {
  const isRed = emergency.level === 'red';
  
  return (
    <View style={[styles.container, isRed ? styles.redStrip : styles.amberStrip]}>
      <View style={styles.content}>
        <Text style={[styles.reasonText, isRed ? styles.redText : styles.amberText]}>
          {emergency.reason}
        </Text>
        
        <TouchableOpacity
          style={[styles.ctaButton, isRed ? styles.redButton : styles.amberButton]}
          onPress={onEmergencyAction}
          accessible={true}
          accessibilityRole="button"
          accessibilityLabel={`Emergency action: ${emergency.cta}`}
        >
          <Text style={[styles.ctaText, isRed ? styles.redButtonText : styles.amberButtonText]}>
            {emergency.cta}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
    marginBottom: 16,
    // Shadow for iOS
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    // Elevation for Android
    elevation: 2,
  },
  redStrip: {
    backgroundColor: '#FEE2E2', // Red-50
    borderLeftWidth: 4,
    borderLeftColor: '#DC2626', // Red-600
  },
  amberStrip: {
    backgroundColor: '#FEF3C7', // Amber-50
    borderLeftWidth: 4,
    borderLeftColor: '#D97706', // Amber-600
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  reasonText: {
    flex: 1,
    fontSize: 14,
    fontWeight: '500',
    marginRight: 12,
    lineHeight: 20,
  },
  redText: {
    color: '#991B1B', // Red-800
  },
  amberText: {
    color: '#92400E', // Amber-800
  },
  ctaButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
    minHeight: 44, // Ensure good touch target
  },
  redButton: {
    backgroundColor: '#DC2626', // Red-600
  },
  amberButton: {
    backgroundColor: '#D97706', // Amber-600
  },
  ctaText: {
    fontSize: 13,
    fontWeight: '600',
    textAlign: 'center',
  },
  redButtonText: {
    color: '#FFFFFF',
  },
  amberButtonText: {
    color: '#FFFFFF',
  },
});

export default EmergencyStrip;
