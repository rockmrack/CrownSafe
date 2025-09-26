// Example usage of ExplainResultButton in your Scan Result screen
// This is a demonstration file showing how to integrate the chat feature

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { ExplainResultButton } from "./ExplainResult";

// Mock scan result data structure (adjust to match your actual data model)
interface ScanResult {
  scanId: string;
  productName: string;
  barcode: string;
  safetyStatus: "safe" | "warning" | "danger";
  recalls: any[];
  // ... other fields
}

interface ScanResultScreenProps {
  scanResult: ScanResult;
}

export const ScanResultScreen: React.FC<ScanResultScreenProps> = ({ scanResult }) => {
  const handleFeedback = (helpful: boolean) => {
    // TODO: Replace with your analytics tracking
    // Example: Analytics.track("explain_result_feedback", { 
    //   scanId: scanResult.scanId, 
    //   helpful: helpful,
    //   timestamp: new Date().toISOString()
    // });
    console.log(`Feedback for scan ${scanResult.scanId}: ${helpful ? 'helpful' : 'not helpful'}`);
  };

  return (
    <View style={styles.container}>
      {/* Your existing scan result UI */}
      <Text style={styles.title}>{scanResult.productName}</Text>
      <Text style={styles.barcode}>Barcode: {scanResult.barcode}</Text>
      
      {/* Safety status display */}
      <View style={[
        styles.statusBadge, 
        { backgroundColor: getStatusColor(scanResult.safetyStatus) }
      ]}>
        <Text style={styles.statusText}>{scanResult.safetyStatus.toUpperCase()}</Text>
      </View>

      {/* Recalls list */}
      {scanResult.recalls?.length > 0 && (
        <View style={styles.recallsSection}>
          <Text style={styles.sectionTitle}>Recalls Found:</Text>
          {scanResult.recalls.map((recall, index) => (
            <Text key={index} style={styles.recallItem}>• {recall.title}</Text>
          ))}
        </View>
      )}

      {/* NEW: Explain This Result Button */}
      <View style={styles.explainSection}>
        <ExplainResultButton 
          baseUrl={process.env.EXPO_PUBLIC_API_BASE as string}
          scanId={scanResult.scanId}
          onFeedback={handleFeedback}
        />
      </View>
    </View>
  );
};

// Helper function for status colors
function getStatusColor(status: string): string {
  switch (status) {
    case "safe": return "#dcfce7";
    case "warning": return "#fef3c7";
    case "danger": return "#fee2e2";
    default: return "#f3f4f6";
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: "#ffffff",
  },
  title: {
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 8,
  },
  barcode: {
    fontSize: 14,
    color: "#6b7280",
    marginBottom: 12,
  },
  statusBadge: {
    alignSelf: "flex-start",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginBottom: 16,
  },
  statusText: {
    fontSize: 12,
    fontWeight: "600",
  },
  recallsSection: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 8,
  },
  recallItem: {
    fontSize: 14,
    marginBottom: 4,
  },
  explainSection: {
    marginTop: 20,
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: "#e5e7eb",
  },
});
