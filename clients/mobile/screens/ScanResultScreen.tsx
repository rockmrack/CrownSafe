// clients/mobile/screens/ScanResultScreen.tsx
import React from "react";
import { View, Text, ScrollView, StyleSheet } from "react-native";
import { VerdictCard } from "../components/VerdictCard";
import { mapScanToVerdict } from "../utils/verdict";
import { ExplainResultButton } from "../components/ExplainResult"; // from Task 0.3
import { ChatBox } from "../components/ChatBox";

export interface ScanResultScreenProps {
  scanId: string;
  scanData: any;
  apiBase: string;
  productName?: string;
  barcode?: string;
  onFeedback?: (helpful: boolean) => void;
}

export const ScanResultScreen: React.FC<ScanResultScreenProps> = ({ 
  scanId, 
  scanData, 
  apiBase, 
  productName, 
  barcode,
  onFeedback 
}) => {
  const mapped = mapScanToVerdict({
    recalls_found: scanData?.recall_count ?? scanData?.recalls_found,
    key_flags: scanData?.key_flags ?? scanData?.flags ?? [],
    one_line_reason: scanData?.one_line_reason,
  });

  const handleExplain = () => {
    // This will be handled by the ExplainResultButton component
    // The VerdictCard's onExplain is just for visual consistency
  };

  const handleSetAlert = () => {
    // TODO: wire alert in later task
    console.log('Set recall alert for scanId:', scanId);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {/* Product Info Header */}
      {(productName || barcode) && (
        <View style={styles.productHeader}>
          {productName && <Text style={styles.productName}>{productName}</Text>}
          {barcode && <Text style={styles.barcode}>Barcode: {barcode}</Text>}
        </View>
      )}

      {/* Safety Verdict Card - Top of Screen */}
      <VerdictCard
        verdict={mapped.verdict}
        oneLine={mapped.oneLine}
        flags={mapped.flags}
        onExplain={handleExplain}
        onSetAlert={mapped.verdict === "recall" ? handleSetAlert : undefined}
      />

      {/* Explain This Result Button */}
      <View style={styles.explainSection}>
        <ExplainResultButton 
          baseUrl={apiBase} 
          scanId={scanId} 
          onFeedback={onFeedback || ((helpful) => {
            // Default analytics tracking
            console.log(`Explanation feedback for ${scanId}: ${helpful ? 'helpful' : 'not helpful'}`);
          })} 
        />
      </View>

      {/* Chat Box for Interactive Questions */}
      <View style={styles.chatSection}>
        <Text style={styles.sectionTitle}>Ask Questions</Text>
        <ChatBox 
          apiBase={apiBase} 
          scanId={scanId} 
          smartChips={["Pregnancy risk?", "Allergies?", "Recall details"]} 
        />
      </View>

      {/* Additional scan details could go here */}
      {scanData?.additional_info && (
        <View style={styles.additionalInfo}>
          <Text style={styles.sectionTitle}>Additional Information</Text>
          <Text style={styles.infoText}>{scanData.additional_info}</Text>
        </View>
      )}

      {/* Recalls list if available */}
      {scanData?.recalls && scanData.recalls.length > 0 && (
        <View style={styles.recallsSection}>
          <Text style={styles.sectionTitle}>Recall Details</Text>
          {scanData.recalls.map((recall: any, index: number) => (
            <View key={index} style={styles.recallItem}>
              <Text style={styles.recallTitle}>{recall.title || recall.description}</Text>
              {recall.date && (
                <Text style={styles.recallDate}>Date: {recall.date}</Text>
              )}
              {recall.agency && (
                <Text style={styles.recallAgency}>Agency: {recall.agency}</Text>
              )}
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#ffffff",
  },
  contentContainer: {
    padding: 16,
    gap: 16,
  },
  productHeader: {
    marginBottom: 8,
  },
  productName: {
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 4,
  },
  barcode: {
    fontSize: 14,
    color: "#6b7280",
  },
  explainSection: {
    // Styling handled by ExplainResultButton component
  },
  chatSection: {
    minHeight: 300,
    maxHeight: 400,
    padding: 12,
    backgroundColor: "#f9fafb",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#e5e7eb",
  },
  additionalInfo: {
    padding: 12,
    backgroundColor: "#f9fafb",
    borderRadius: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 8,
  },
  infoText: {
    fontSize: 14,
    lineHeight: 20,
  },
  recallsSection: {
    padding: 12,
    backgroundColor: "#fef2f2",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#fecaca",
  },
  recallItem: {
    marginBottom: 12,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#fee2e2",
  },
  recallTitle: {
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 4,
  },
  recallDate: {
    fontSize: 12,
    color: "#6b7280",
    marginBottom: 2,
  },
  recallAgency: {
    fontSize: 12,
    color: "#6b7280",
  },
});
