// clients/mobile/examples/PrivacySettingsExample.tsx
import React from 'react';
import { View } from 'react-native';
import { PrivacySettingsScreen } from '../screens/PrivacySettingsScreen';

// Example: How to integrate Privacy Settings into your app

export const PrivacySettingsExample: React.FC = () => {
  // In a real app, you'd get these from your environment/auth system
  const apiBase = process.env.EXPO_PUBLIC_API_BASE as string || 'https://babyshield.cureviax.ai';
  const authToken = undefined; // Replace with your auth token if required

  return (
    <View style={{ flex: 1 }}>
      <PrivacySettingsScreen 
        apiBase={apiBase} 
        authToken={authToken} 
      />
    </View>
  );
};

// Example: How to add to React Navigation
/*
import { createStackNavigator } from '@react-navigation/stack';

const Stack = createStackNavigator();

export const AppNavigator = () => (
  <Stack.Navigator>
    <Stack.Screen name="Home" component={HomeScreen} />
    <Stack.Screen 
      name="PrivacySettings" 
      component={PrivacySettingsScreen} 
      options={{ title: 'Privacy & Personalization' }}
      initialParams={{
        apiBase: process.env.EXPO_PUBLIC_API_BASE,
        authToken: undefined, // Your auth token here
      }}
    />
  </Stack.Navigator>
);
*/

// Example: How to present as a modal
/*
import { Modal } from 'react-native';

export const SettingsModal: React.FC<{ visible: boolean; onClose: () => void }> = ({ visible, onClose }) => (
  <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
    <PrivacySettingsScreen 
      apiBase={process.env.EXPO_PUBLIC_API_BASE as string}
      authToken={undefined} // Your auth token here
    />
  </Modal>
);
*/
