import React from 'react';
import { View } from 'react-native'; // @ts-ignore
import { ChatBox, EmergencyGuidance } from '../index';
import { createMockNavigation } from '../utils/navigation';

/**
 * Example showing how to integrate EmergencyGuidance with ChatBox
 */
export const EmergencyGuidanceExample: React.FC = () => {
  const mockNavigation = createMockNavigation();

  return (
    <View style={{ flex: 1 }}>
      {/* ChatBox with navigation for emergency CTA */}
      <ChatBox
        apiBase="https://babyshield.cureviax.ai"
        scanId="example_scan_123"
        navigation={mockNavigation}
        smartChips={["Is this safe in pregnancy?", "Any allergen concerns?", "What alternatives?"]}
      />
    </View>
  );
};

/**
 * Example of EmergencyGuidance screen with different jurisdictions
 */
export const EmergencyGuidanceExamples: React.FC = () => {
  return (
    <View style={{ flex: 1 }}>
      {/* EU jurisdiction */}
      <EmergencyGuidance 
        route={{ 
          params: { 
            jurisdictionCode: "EU",
            locale: "en-GB" 
          } 
        }} 
      />
      
      {/* US jurisdiction */}
      <EmergencyGuidance 
        route={{ 
          params: { 
            jurisdictionCode: "US",
            locale: "en-US" 
          } 
        }} 
      />
      
      {/* Unknown jurisdiction (fallback) */}
      <EmergencyGuidance />
    </View>
  );
};

/**
 * Example of proper React Navigation integration
 */
export const NavigationExample = `
// In your main App.tsx or navigation setup:

import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { EmergencyGuidance, ScanResultScreen } from 'babyshield-mobile';

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen 
          name="ScanResult" 
          component={ScanResultScreen}
          options={{ title: "Scan Results" }}
        />
        <Stack.Screen
          name="EmergencyGuidance"
          component={EmergencyGuidance}
          options={{ 
            title: "Emergency Guidance", 
            headerBackTitle: "Back",
            presentation: 'modal' // Optional: present as modal for urgency
          }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

// Then in your ChatBox usage:
<ChatBox
  apiBase="https://babyshield.cureviax.ai"
  scanId={scanId}
  navigation={navigation} // Pass navigation from screen props
/>
`;

export default EmergencyGuidanceExample;
