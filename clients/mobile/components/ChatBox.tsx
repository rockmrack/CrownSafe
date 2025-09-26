// clients/mobile/components/ChatBox.tsx
import React, { useCallback, useMemo, useRef, useState } from "react"; // @ts-ignore
import { View, Text, TextInput, Pressable, ScrollView, ActivityIndicator, Alert } from "react-native"; // @ts-ignore
import { EmergencyStrip } from './EmergencyStrip';
import { SuggestedQuestions } from './SuggestedQuestions';
import { NavigationProp, createMockNavigation, createEmergencyActionHandler } from '../utils/navigation';

export type Intent =
  | "pregnancy_risk"
  | "allergy_question"
  | "ingredient_info"
  | "age_appropriateness"
  | "alternative_products"
  | "recall_details"
  | "unclear_intent";

export type EmergencyNotice = {
  level: "red" | "amber";
  reason: string;
  cta: string;
};

export type ExplanationResponse = {
  summary: string;
  reasons: string[];
  checks: string[];
  flags: string[];
  disclaimer: string;
  // Optional future field; render if present
  evidence?: Array<{ type: string; source: string; id?: string; url?: string | null }>;
  suggested_questions?: string[];
  emergency?: EmergencyNotice;
};

export type ConversationResponse = {
  conversation_id: string;
  intent: Intent;
  message: ExplanationResponse;
  trace_id: string;
  tool_calls: Array<{ name: string; latency_ms: number; ok: boolean; error?: string | null }>;
};

async function sendMessage(
  apiBase: string, 
  scanId: string, 
  userQuery: string, 
  conversationId?: string,
  unclearCount: number = 0
): Promise<ConversationResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  
  // Add unclear count header for loop prevention
  if (unclearCount > 0) {
    headers["X-Chat-Unclear-Count"] = String(unclearCount);
  }
  
  const res = await fetch(`${apiBase}/api/v1/chat/conversation`, {
    method: "POST",
    headers,
    body: JSON.stringify({ scan_id: scanId, user_query: userQuery, conversation_id: conversationId }),
  });
  if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
  return (await res.json()) as ConversationResponse;
}

const Badge: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <View style={{ paddingHorizontal: 8, paddingVertical: 4, backgroundColor: "#e5e7eb", borderRadius: 999, marginRight: 6, marginBottom: 6 }}>
    <Text style={{ fontSize: 12, color: "#374151" }}>{children}</Text>
  </View>
);

const Section: React.FC<{ title: string }> = ({ title, children }) => (
  <View style={{ marginTop: 10 }}>
    <Text style={{ fontWeight: "700", marginBottom: 6 }}>{title}</Text>
    <View>{children}</View>
  </View>
);

// EmergencyStrip component now imported from separate file

type Msg = { role: "user" | "assistant"; content: string | ExplanationResponse; intent?: Intent; trace_id?: string };

export const ChatBox: React.FC<{
  apiBase: string;
  scanId: string;
  smartChips?: string[]; // e.g., ["Pregnancy risk?", "Allergies?", "Alternatives?"]
  navigation?: NavigationProp;
}> = ({ apiBase, scanId, smartChips = ["Pregnancy risk?", "Allergies?", "Alternatives?"], navigation }) => {
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [unclearCount, setUnclearCount] = useState(0);
  const scrollRef = useRef<ScrollView>(null);

  const onSend = useCallback(async (q: string) => {
    if (!q.trim() || busy) return;
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: q }]);
    try {
      const resp = await sendMessage(apiBase, scanId, q, conversationId, unclearCount);
      setConversationId(resp.conversation_id);
      setMessages((m) => [...m, { role: "assistant", content: resp.message, intent: resp.intent, trace_id: resp.trace_id }]);
      
      // Track unclear responses for loop prevention
      if (resp.intent === "unclear_intent") {
        setUnclearCount(prev => prev + 1);
      } else {
        setUnclearCount(0); // Reset on successful intent
      }
      
      setText("");
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50);
    } catch (e: any) {
      Alert.alert("Chat error", e?.message ?? "Please try again.");
    } finally {
      setBusy(false);
    }
  }, [apiBase, scanId, conversationId, busy, unclearCount]);

  const onChip = useCallback((label: string) => onSend(label), [onSend]);

  const chipRow = useMemo(() => (
    <View style={{ flexDirection: "row", flexWrap: "wrap", marginBottom: 8 }}>
      {smartChips.map((c) => (
        <Pressable key={c} onPress={() => onChip(c)} style={{ paddingHorizontal: 10, paddingVertical: 8, backgroundColor: "#e0e7ff", borderRadius: 999, marginRight: 8, marginBottom: 8 }}>
          <Text style={{ fontWeight: "600" }}>{c}</Text>
        </Pressable>
      ))}
    </View>
  ), [smartChips, onChip]);

  return (
    <View style={{ flex: 1 }}>
      <EmergencyStrip />
      {chipRow}

      <ScrollView ref={scrollRef} contentContainerStyle={{ paddingBottom: 12 }}>
        {messages.map((m, i) => (
          <View key={i} style={{ marginBottom: 12, alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "92%" }}>
            {m.role === "user" ? (
              <View style={{ backgroundColor: "#dbeafe", padding: 10, borderRadius: 12 }}>
                <Text>{String(m.content)}</Text>
              </View>
            ) : (
              <View style={{ backgroundColor: "#f8fafc", padding: 12, borderRadius: 12, borderWidth: 1, borderColor: "#e5e7eb" }}>
                {typeof m.content === "object" ? (
                  <>
                    <Text style={{ fontWeight: "700", marginBottom: 6 }}>Answer</Text>
                    <Text style={{ marginBottom: 6 }}>{m.content.summary}</Text>

                    {m.content.reasons?.length > 0 && (
                      <Section title="Why">
                        {m.content.reasons.map((r, idx) => <Text key={idx}>• {r}</Text>)}
                      </Section>
                    )}

                    {m.content.checks?.length > 0 && (
                      <Section title="Check on the label">
                        {m.content.checks.map((c, idx) => <Text key={idx}>• {c}</Text>)}
                      </Section>
                    )}

                    {m.content.flags?.length > 0 && (
                      <View style={{ flexDirection: "row", flexWrap: "wrap", marginTop: 8 }}>
                        {m.content.flags.map((f, idx) => <Badge key={idx}>{f}</Badge>)}
                      </View>
                    )}

                    {(m.content as any)?.jurisdiction?.label && (
                      <Badge>{(m.content as any).jurisdiction.label}</Badge>
                    )}

                    {!!m.content.evidence && m.content.evidence.length > 0 && (
                      <Section title="Evidence">
                        <View style={{ flexDirection: "row", flexWrap: "wrap" }}>
                          {m.content.evidence.map((e, idx) => (
                            <Badge key={idx}>{`${e.source}${e.id ? " · " + e.id : ""}`}</Badge>
                          ))}
                        </View>
                      </Section>
                    )}

                    {/* Emergency Strip */}
                    {m.content.emergency && (
                      <View style={{ marginTop: 12, marginBottom: 8 }}>
                        <EmergencyStrip 
                          emergency={m.content.emergency}
                          jurisdictionCode={(m.content as any)?.jurisdiction?.code || null}
                          onEmergencyAction={createEmergencyActionHandler(
                            navigation || createMockNavigation(),
                            (m.content as any)?.jurisdiction?.code || null,
                            null, // locale - could be added later
                            apiBase
                          )}
                        />
                      </View>
                    )}

                    {/* Suggested Questions */}
                    {m.content.suggested_questions && m.content.suggested_questions.length > 0 && (
                      <SuggestedQuestions 
                        questions={m.content.suggested_questions}
                        onQuestionSelect={(question) => {
                          setText(question);
                          // Could auto-send or let user edit first
                        }}
                        maxItems={3}
                      />
                    )}

                    <Text style={{ fontSize: 12, color: "#6b7280", marginTop: 10 }}>{m.content.disclaimer}</Text>
                    {m.intent && <Text style={{ fontSize: 10, color: "#94a3b8", marginTop: 4 }}>Intent: {m.intent} · Trace: {m.trace_id}</Text>}
                  </>
                ) : (
                  <Text>{String(m.content)}</Text>
                )}
              </View>
            )}
          </View>
        ))}
        {busy && (
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <ActivityIndicator />
            <Text>Thinking…</Text>
          </View>
        )}
      </ScrollView>

      <View style={{ flexDirection: "row", gap: 8, marginTop: 8 }}>
        <TextInput
          value={text}
          onChangeText={setText}
          placeholder="Ask a question about this product…"
          style={{ flex: 1, borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, backgroundColor: "white" }}
          autoCapitalize="sentences"
          returnKeyType="send"
          onSubmitEditing={() => onSend(text)}
        />
        <Pressable onPress={() => onSend(text)} disabled={busy || !text.trim()} style={{ paddingHorizontal: 16, justifyContent: "center", borderRadius: 10, backgroundColor: busy || !text.trim() ? "#cbd5e1" : "#6366f1" }}>
          <Text style={{ color: "white", fontWeight: "700" }}>Send</Text>
        </Pressable>
      </View>
    </View>
  );
};
