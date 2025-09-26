/**
 * Navigation utilities for BabyShield mobile app.
 * Provides helper functions for screen navigation.
 */

export interface NavigationParams {
  EmergencyGuidance?: {
    jurisdictionCode?: string | null;
    locale?: string | null;
  };
  [key: string]: any;
}

export interface NavigationProp {
  navigate: (screenName: keyof NavigationParams, params?: NavigationParams[keyof NavigationParams]) => void;
  goBack: () => void;
  canGoBack: () => boolean;
}

/**
 * Mock navigation for development/testing when React Navigation is not available.
 */
export const createMockNavigation = (): NavigationProp => ({
  navigate: (screenName: string, params?: any) => {
    console.log(`[Mock Navigation] Navigate to ${screenName}`, params);
    // In a real app, this would be handled by React Navigation
    alert(`Would navigate to ${screenName} screen`);
  },
  goBack: () => {
    console.log('[Mock Navigation] Go back');
    // In a real app, this would go back in the navigation stack
  },
  canGoBack: () => {
    console.log('[Mock Navigation] Can go back check');
    return true;
  },
});

/**
 * Navigate to Emergency Guidance screen with jurisdiction context.
 */
export const navigateToEmergencyGuidance = (
  navigation: NavigationProp,
  jurisdictionCode?: string | null,
  locale?: string | null
) => {
  navigation.navigate('EmergencyGuidance', {
    jurisdictionCode,
    locale,
  });
};

/**
 * Create emergency action handler that navigates to Emergency Guidance.
 */
export const createEmergencyActionHandler = (
  navigation: NavigationProp,
  jurisdictionCode?: string | null,
  locale?: string | null,
  analyticsUrl?: string
) => {
  return () => {
    // Optional analytics ping (fire-and-forget)
    if (analyticsUrl) {
      fetch(`${analyticsUrl}/api/v1/analytics/emergency-open`, { 
        method: "POST" 
      }).catch(() => {
        // Ignore analytics failures - emergency guidance is more important
      });
    }

    // Navigate to Emergency Guidance screen
    navigateToEmergencyGuidance(navigation, jurisdictionCode, locale);
  };
};
