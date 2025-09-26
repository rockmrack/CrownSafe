// clients/mobile/components/VerdictCard.tsx
import React from "react";
import { View, Text, Pressable } from "react-native";

export type Verdict = "safe" | "caution" | "avoid" | "recall";

export type VerdictCardProps = {
  verdict: Verdict;
  oneLine: string;            // short reason, one sentence
  flags?: string[];           // e.g. ["contains_peanuts","soft_cheese"]
  onExplain?: () => void;     // opens Explain modal (Phase 0)
  onSetAlert?: () => void;    // optional: set recall alert
};

const badgeStyles: Record<Verdict, { bg: string; emoji: string; label: string }> = {
  safe:    { bg: "#dcfce7", emoji: "✅", label: "No Recalls Found" },
  caution: { bg: "#fef3c7", emoji: "⚠️", label: "Caution Advised" },
  avoid:   { bg: "#fee2e2", emoji: "⛔", label: "Avoid" },
  recall:  { bg: "#fecaca", emoji: "❌", label: "Recall Alert" },
};

export const VerdictCard: React.FC<VerdictCardProps> = ({ verdict, oneLine, flags = [], onExplain, onSetAlert }) => {
  const s = badgeStyles[verdict];
  return (
    <View testID="verdict-card" style={{ padding: 16, borderRadius: 12, backgroundColor: s.bg, gap: 8 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        <Text style={{ fontSize: 22 }}>{s.emoji}</Text>
        <Text style={{ fontSize: 18, fontWeight: "700" }}>{s.label}</Text>
      </View>

      <Text style={{ fontSize: 14 }}>{oneLine}</Text>

      {flags.length > 0 && (
        <Text style={{ fontSize: 12, color: "#475569" }}>
          Flags: {flags.join(", ")}
        </Text>
      )}

      <View style={{ flexDirection: "row", gap: 12, marginTop: 8 }}>
        {!!onExplain && (
          <Pressable onPress={onExplain} testID="btn-explain" style={{ paddingVertical: 10, paddingHorizontal: 12, backgroundColor: "#e0e7ff", borderRadius: 8 }}>
            <Text style={{ fontWeight: "600" }}>Explain</Text>
          </Pressable>
        )}
        {!!onSetAlert && (
          <Pressable onPress={onSetAlert} testID="btn-alert" style={{ paddingVertical: 10, paddingHorizontal: 12, backgroundColor: "#f1f5f9", borderRadius: 8 }}>
            <Text>Set recall alert</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
};
