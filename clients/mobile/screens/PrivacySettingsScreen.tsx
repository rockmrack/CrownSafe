// clients/mobile/screens/PrivacySettingsScreen.tsx
import React, { useEffect, useState } from "react";
import { View, Text, Switch, TextInput, Pressable, ActivityIndicator, Alert, ScrollView } from "react-native";
import { getProfile, putProfile, type Profile } from "../api/chatProfile";

type Props = { apiBase: string; authToken?: string };

export const PrivacySettingsScreen: React.FC<Props> = ({ apiBase, authToken }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [p, setP] = useState<Profile>({
    consent_personalization: false,
    memory_paused: false,
    allergies: [],
    pregnancy_trimester: null,
    pregnancy_due_date: null,
    child_birthdate: null,
  });

  useEffect(() => {
    (async () => {
      try {
        const prof = await getProfile(apiBase, authToken);
        setP({ ...p, ...prof });
      } catch (e: any) {
        // If 401, the backend placeholder may require auth; surface gently.
        Alert.alert("Profile", e?.message ?? "Unable to load profile.");
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, authToken]);

  const save = async () => {
    try {
      setSaving(true);
      await putProfile(apiBase, p, authToken);
      Alert.alert("Saved", "Your preferences have been updated.");
    } catch (e: any) {
      Alert.alert("Save failed", e?.message ?? "Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const set = <K extends keyof Profile>(k: K, v: Profile[K]) => setP((prev) => ({ ...prev, [k]: v }));

  const eraseHistory = async () => {
    try {
      const res = await fetch(`${apiBase}/api/v1/chat/erase-history`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}) },
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body?.detail || `HTTP ${res.status}`);
      Alert.alert("Erased", `Conversation history ${body.mode === "async" ? "scheduled" : "deleted"} (${body.deleted} thread(s)).`);
    } catch (e: any) {
      Alert.alert("Erase failed", e?.message ?? "Please try again.");
    }
  };

  if (loading) return <View style={{ padding: 16 }}><ActivityIndicator testID="activity-indicator" /></View>;

  return (
    <ScrollView contentContainerStyle={{ padding: 16 }}>
      <Text style={{ fontSize: 20, fontWeight: "700", marginBottom: 12 }}>Personalization & Data</Text>
      <Text style={{ color: "#475569", marginBottom: 16 }}>
        Opt in to remember allergies, trimester, and your child's age for more tailored safety answers. You can pause or erase anytime.
      </Text>

      {/* Consent */}
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <Text style={{ fontWeight: "600" }}>Personalization consent</Text>
        <Switch value={p.consent_personalization} onValueChange={(v) => set("consent_personalization", v)} />
      </View>

      {/* Pause */}
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Text style={{ fontWeight: "600" }}>Pause memory</Text>
        <Switch value={p.memory_paused} onValueChange={(v) => set("memory_paused", v)} />
      </View>

      {/* Allergies */}
      <Text style={{ fontWeight: "600" }}>Family allergies (comma-separated)</Text>
      <TextInput
        placeholder="e.g., peanuts, dairy, soy"
        value={p.allergies.join(", ")}
        onChangeText={(t) => set("allergies", t.split(",").map((s) => s.trim()).filter(Boolean))}
        style={{ borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 8, padding: 10, marginTop: 6, marginBottom: 12, backgroundColor: "white" }}
      />

      {/* Trimester */}
      <Text style={{ fontWeight: "600" }}>Pregnancy trimester (1–3, blank if not applicable)</Text>
      <TextInput
        keyboardType="number-pad"
        placeholder="1, 2, or 3"
        value={p.pregnancy_trimester?.toString() ?? ""}
        onChangeText={(t) => {
          const n = t.trim() ? parseInt(t, 10) : NaN;
          set("pregnancy_trimester", Number.isFinite(n) && n >= 1 && n <= 3 ? n : null);
        }}
        style={{ borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 8, padding: 10, marginTop: 6, marginBottom: 12, backgroundColor: "white" }}
      />

      {/* Dates */}
      <Text style={{ fontWeight: "600" }}>Due date (YYYY-MM-DD)</Text>
      <TextInput
        placeholder="YYYY-MM-DD"
        value={p.pregnancy_due_date ?? ""}
        onChangeText={(t) => set("pregnancy_due_date", t.trim() || null)}
        style={{ borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 8, padding: 10, marginTop: 6, marginBottom: 12, backgroundColor: "white" }}
        autoCapitalize="none"
      />

      <Text style={{ fontWeight: "600" }}>Child birthdate (YYYY-MM-DD)</Text>
      <TextInput
        placeholder="YYYY-MM-DD"
        value={p.child_birthdate ?? ""}
        onChangeText={(t) => set("child_birthdate", t.trim() || null)}
        style={{ borderWidth: 1, borderColor: "#e5e7eb", borderRadius: 8, padding: 10, marginTop: 6, marginBottom: 12, backgroundColor: "white" }}
        autoCapitalize="none"
      />

      {/* Actions */}
      <View style={{ flexDirection: "row", gap: 10, marginTop: 8 }}>
        <Pressable onPress={save} disabled={saving} style={{ backgroundColor: saving ? "#cbd5e1" : "#16a34a", paddingVertical: 12, paddingHorizontal: 16, borderRadius: 10 }}>
          <Text style={{ color: "white", fontWeight: "700" }}>{saving ? "Saving…" : "Save"}</Text>
        </Pressable>

        <Pressable
          onPress={() => Alert.alert(
            "Erase conversation history",
            "This will delete your saved chat messages. You'll keep access to the app.",
            [
              { text: "Cancel", style: "cancel" },
              { text: "OK", onPress: eraseHistory },
            ]
          )}
          style={{ backgroundColor: "#ef4444", paddingVertical: 12, paddingHorizontal: 16, borderRadius: 10 }}
        >
          <Text style={{ color: "white", fontWeight: "700" }}>Erase history</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
};
