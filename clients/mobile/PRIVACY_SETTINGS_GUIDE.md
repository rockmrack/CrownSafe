# Privacy Settings Integration Guide

## Overview

The Privacy Settings feature allows users to opt-in to personalized chat responses while maintaining privacy-first defaults. Users can manage their consent, pause memory, and configure personal information like allergies and pregnancy details.

## Features

### Privacy-First Design
- **Consent required**: Personalization is disabled by default
- **Memory pause**: Users can temporarily pause data collection
- **Transparent controls**: Clear toggles for all privacy settings
- **Erase option**: Users can request deletion of conversation history

### Personalization Options
- **Allergies**: Comma-separated list of family allergies
- **Pregnancy**: Trimester (1-3) and due date tracking
- **Child age**: Child birthdate for age-appropriate guidance
- **Memory management**: Pause/resume data collection anytime

## API Integration

### Profile Type
```typescript
type Profile = {
  consent_personalization: boolean;
  memory_paused: boolean;
  allergies: string[];
  pregnancy_trimester?: number | null;
  pregnancy_due_date?: string | null; // ISO yyyy-mm-dd
  child_birthdate?: string | null;    // ISO yyyy-mm-dd
};
```

### API Functions
```typescript
// Get current profile
const profile = await getProfile(apiBase, authToken);

// Update profile
const result = await putProfile(apiBase, profileData, authToken);
```

## Component Usage

### Basic Integration
```tsx
import { PrivacySettingsScreen } from '@babyshield/mobile';

export const SettingsPage = () => (
  <PrivacySettingsScreen 
    apiBase="https://babyshield.cureviax.ai"
    authToken={userToken} // Optional
  />
);
```

### Navigation Integration
```tsx
import { createStackNavigator } from '@react-navigation/stack';

const Stack = createStackNavigator();

export const AppNavigator = () => (
  <Stack.Navigator>
    <Stack.Screen 
      name="PrivacySettings" 
      component={PrivacySettingsScreen}
      options={{ title: 'Privacy & Personalization' }}
      initialParams={{
        apiBase: process.env.EXPO_PUBLIC_API_BASE,
        authToken: userAuthToken,
      }}
    />
  </Stack.Navigator>
);
```

### Modal Integration
```tsx
import { Modal } from 'react-native';

export const SettingsModal: React.FC<{
  visible: boolean;
  onClose: () => void;
}> = ({ visible, onClose }) => (
  <Modal visible={visible} animationType="slide">
    <PrivacySettingsScreen 
      apiBase={process.env.EXPO_PUBLIC_API_BASE as string}
      authToken={userToken}
    />
    <Pressable onPress={onClose}>
      <Text>Close</Text>
    </Pressable>
  </Modal>
);
```

## User Experience

### Loading States
- Shows activity indicator while fetching profile
- Graceful error handling for network issues
- Clear feedback for save operations

### Form Validation
- Pregnancy trimester limited to 1-3
- Date fields accept YYYY-MM-DD format
- Allergies parsed from comma-separated text
- Invalid inputs are rejected with clear feedback

### Privacy Messaging
- Clear explanation of data usage
- Emphasis on user control and consent
- Transparent about what data is collected
- Easy access to pause or erase data

## Error Handling

### Network Errors
- Graceful handling of API failures
- User-friendly error messages
- Retry mechanisms where appropriate

### Validation Errors
- Client-side validation for form fields
- Server-side validation feedback
- Clear indication of invalid inputs

### Authentication
- Handles missing auth tokens gracefully
- Clear messaging when auth is required
- Fallback behavior for unauthenticated users

## Testing

### Unit Tests
- API client functionality
- Form validation logic
- Error handling scenarios
- User interaction flows

### Integration Tests
- End-to-end privacy settings flow
- Backend API integration
- Cross-platform compatibility

## Privacy Compliance

### GDPR Compliance
- Clear consent mechanisms
- Right to pause data collection
- Right to erasure (deletion)
- Transparent data usage

### Data Minimization
- Only collect necessary information
- User controls what data is stored
- Clear purpose for each data field
- Easy opt-out mechanisms

## Customization

### Styling
The component uses inline styles that can be customized by:
- Wrapping in a styled container
- Using React Native style inheritance
- Theming through context providers

### Localization
Text strings can be localized by:
- Extracting strings to translation files
- Using i18n libraries like react-i18next
- Providing locale-specific date formats

### Branding
- Customize colors and fonts
- Add company branding elements
- Modify button styles and layouts
- Add custom icons or illustrations
