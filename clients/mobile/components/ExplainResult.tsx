// components/ExplainResult.tsx
import React, { useState } from "react"; // @ts-ignore
import { View, Text, Pressable, ActivityIndicator, Modal, ScrollView, Alert } from "react-native"; // @ts-ignore
import AlternativesList from './AlternativesList';

type ExplanationResponse = {
  summary: string;
  reasons: string[];
  checks: string[];
  flags: string[];
  disclaimer: string;
  alternatives?: {
    items: Array<{
      id: string;
      name: string;
      brand?: string;
      category?: string;
      reason: string;
      tags: string[];
      pregnancy_safe?: boolean;
      allergy_safe_for: string[];
      age_min_months?: number;
      link_url?: string;
      evidence: Array<{
        type: "recall" | "regulation" | "guideline" | "datasheet" | "label";
        source: string;
        id?: string;
        url?: string;
      }>;
    }>;
  };
};

async function fetchExplainResult(baseUrl: string, scanId: string): Promise<ExplanationResponse> {
  const res = await fetch(`${baseUrl}/api/v1/chat/explain-result`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scan_id: scanId }),
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || `HTTP ${res.status}`);
  }
  return (await res.json()) as ExplanationResponse;
}

export const ExplainResultButton: React.FC<{ baseUrl: string; scanId: string; onFeedback?: (helpful: boolean) => void }> = ({ baseUrl, scanId, onFeedback }) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ExplanationResponse | null>(null);

  const handleOpen = async () => {
    try {
      setOpen(true);
      setLoading(true);
      const payload = await fetchExplainResult(baseUrl, scanId);
      setData(payload);
    } catch (e: any) {
      Alert.alert("Explain failed", e?.message ?? "Please try again.");
      setOpen(false);
    } finally {
      setLoading(false);
    }
  };

  const sendFeedback = async (helpful: boolean) => {
    try {
      // Send feedback to backend
      const response = await fetch(`${baseUrl}/api/v1/analytics/explain-feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // Optionally pass app context headers:
          "X-Platform": "ios", // or android/web - could be dynamic
          "X-App-Version": "1.0.0", // could come from app config
          "X-Locale": "en-US", // could come from device locale
        },
        body: JSON.stringify({
          scan_id: scanId,
          helpful,
          // If you have trace id from the explain call, pass it here:
          // trace_id: lastTraceIdRef.current,
          // reason/comment optional for 👎 flow (future enhancement)
        }),
      });
      
      if (!response.ok) {
        throw new Error(await response.text());
      }
      
      // Success - could show a brief toast here
      console.log("Feedback sent successfully");
      
    } catch (error) {
      // Non-blocking error: log silently
      console.warn("Failed to send feedback:", error);
      // Could show a brief toast about offline mode
    } finally {
      // Always call the callback and close modal
      onFeedback?.(helpful);
      setOpen(false);
    }
  };

  const handleAlternativeClick = async (scanId: string, altId: string) => {
    try {
      // Send analytics to backend
      await fetch(`${baseUrl}/api/v1/analytics/alt-click`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          scan_id: scanId,
          alt_id: altId,
        }),
      });
    } catch (error) {
      // Non-blocking: log but don't interrupt UX
      console.warn("Failed to record alternative click:", error);
    }
  };

  return (
    <>
      <Pressable onPress={handleOpen} style={{ padding: 12, borderRadius: 8, backgroundColor: "#eef2ff" }}>
        <Text style={{ textAlign: "center", fontWeight: "600" }}>Explain This Result (Beta)</Text>
      </Pressable>

      <Modal visible={open} animationType="slide" onRequestClose={() => setOpen(false)}>
        <View style={{ flex: 1, padding: 16 }}>
          {loading && <ActivityIndicator />}
          {!loading && data && (
            <ScrollView>
              <Text style={{ fontSize: 18, fontWeight: "700", marginBottom: 8 }}>Summary</Text>
              <Text style={{ marginBottom: 12 }}>{data.summary}</Text>

              {data.reasons?.length > 0 && (
                <>
                  <Text style={{ fontSize: 16, fontWeight: "700", marginBottom: 6 }}>Why</Text>
                  {data.reasons.map((r, i) => (
                    <Text key={i}>• {r}</Text>
                  ))}
                  <View style={{ height: 8 }} />
                </>
              )}

              {data.checks?.length > 0 && (
                <>
                  <Text style={{ fontSize: 16, fontWeight: "700", marginBottom: 6 }}>Check on the label</Text>
                  {data.checks.map((c, i) => (
                    <Text key={i}>• {c}</Text>
                  ))}
                  <View style={{ height: 8 }} />
                </>
              )}

                     {data.flags?.length > 0 && (
                       <>
                         <Text style={{ fontSize: 12, color: "#475569", marginTop: 6 }}>Flags: {data.flags.join(", ")}</Text>
                       </>
                     )}

                     {(data as any)?.jurisdiction?.label && (
                       <View style={{ marginTop: 8 }}>
                         <Text style={{ fontSize: 12, color: "#475569" }}>
                           Jurisdiction: {(data as any).jurisdiction.label}
                         </Text>
                       </View>
                     )}

                     {(data as any)?.evidence?.length > 0 && (
                       <>
                         <Text style={{ fontSize: 16, fontWeight: "700", marginTop: 10 }}>Evidence</Text>
                         {(data as any).evidence.map((e: any, i: number) => (
                           <Text key={i} style={{ fontSize: 12 }}>
                             • {e.source}{e.id ? ` · ${e.id}` : ""}{e.url ? ` — ${e.url}` : ""}
                           </Text>
                         ))}
                       </>
                     )}

                     {/* Alternatives Section */}
                     {data.alternatives?.items && data.alternatives.items.length > 0 && (
                       <View style={{ marginTop: 16 }}>
                         <AlternativesList 
                           alternatives={data.alternatives.items} 
                           scanId={scanId}
                           onAlternativeClick={handleAlternativeClick}
                           maxItems={3}
                         />
                       </View>
                     )}

                     <Text style={{ fontSize: 12, color: "#6b7280", marginTop: 12 }}>{data.disclaimer}</Text>

              <View style={{ flexDirection: "row", gap: 12, marginTop: 16 }}>
                <Pressable onPress={() => sendFeedback(true)} style={{ padding: 10, backgroundColor: "#dcfce7", borderRadius: 8 }}>
                  <Text>👍 Helpful</Text>
                </Pressable>
                <Pressable onPress={() => sendFeedback(false)} style={{ padding: 10, backgroundColor: "#fee2e2", borderRadius: 8 }}>
                  <Text>👎 Not helpful</Text>
                </Pressable>
                <Pressable onPress={() => setOpen(false)} style={{ padding: 10, backgroundColor: "#e5e7eb", borderRadius: 8 }}>
                  <Text>Close</Text>
                </Pressable>
              </View>
            </ScrollView>
          )}
        </View>
      </Modal>
    </>
  );
};
