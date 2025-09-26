import React, { useMemo } from "react"; // @ts-ignore
import { ScrollView, View, Text, Pressable, Linking, Platform } from "react-native"; // @ts-ignore

type Props = {
  route?: { params?: { jurisdictionCode?: string | null; locale?: string | null } };
};

// Localized strings for offline support
const STRINGS = {
  en: {
    title: "🚨 Emergency Guidance",
    offline_notice: "This screen works offline. If this may be an emergency, contact local services immediately.",
    local_emergency: "Local emergency",
    emergency_fallback: "Emergency (EU/US)",
    call_now: "Call now",
    dial_help: "If you can't dial from here, use your phone app to call your local emergency number.",
    poison_control: "Poison Control",
    common_emergencies: "Common baby emergencies",
    choking: "• Choking: Seek immediate help.",
    not_breathing: "• Not breathing / turning blue: Call emergency services immediately.",
    swallowed: "• Swallowed battery, chemicals, or medicine: Call emergency services or poison control.",
    allergic: "• Severe allergic reaction: Call emergency services.",
    disclaimer: "BabyShield does not provide medical advice. For urgent situations, contact emergency services immediately."
  },
  es: {
    title: "🚨 Guía de Emergencia",
    offline_notice: "Esta pantalla funciona sin conexión. Si esto puede ser una emergencia, contacte los servicios locales inmediatamente.",
    local_emergency: "Emergencia local",
    emergency_fallback: "Emergencia (EU/US)",
    call_now: "Llamar ahora",
    dial_help: "Si no puede marcar desde aquí, use la aplicación de teléfono para llamar al número de emergencia local.",
    poison_control: "Control de Envenenamiento",
    common_emergencies: "Emergencias comunes del bebé",
    choking: "• Asfixia: Busque ayuda inmediata.",
    not_breathing: "• No respira / se pone azul: Llame a servicios de emergencia inmediatamente.",
    swallowed: "• Tragó batería, químicos o medicina: Llame a servicios de emergencia o control de envenenamiento.",
    allergic: "• Reacción alérgica severa: Llame a servicios de emergencia.",
    disclaimer: "BabyShield no proporciona consejos médicos. Para situaciones urgentes, contacte servicios de emergencia inmediatamente."
  }
};

const NUMBERS: Record<string, string> = {
  EU: "112",
  US: "911",
  CA: "911",
  GB: "999",
  AU: "000",
  NZ: "111",
  IN: "112",
};

function pickNumber(jurisdictionCode?: string | null): { label: string; number: string } {
  const code = (jurisdictionCode || "").toUpperCase();
  if (NUMBERS[code]) return { label: "Local emergency", number: NUMBERS[code] };
  // Safe fallbacks parents will recognize globally
  return { label: "Emergency (EU/US)", number: "112 / 911" };
}

function openDial(number: string) {
  // If it's a pair like "112 / 911", open nothing directly to avoid wrong region—parent will see both.
  if (number.includes("/")) return;
  Linking.openURL(`tel:${number}`).catch(() => {});
}

export default function EmergencyGuidance({ route }: Props) {
  const jurisdiction = route?.params?.jurisdictionCode ?? null;
  const locale = route?.params?.locale ?? null;
  const primary = useMemo(() => pickNumber(jurisdiction), [jurisdiction]);
  
  // Determine language (default to English)
  const lang = (locale?.startsWith('es') || jurisdiction === 'ES') ? 'es' : 'en';
  const strings = STRINGS[lang];
  
  // US-specific poison control
  const showPoisonControl = jurisdiction === 'US';

  return (
    <ScrollView
      contentContainerStyle={{ padding: 16, paddingBottom: 32 }}
      testID="emergency-guidance-screen"
      accessibilityLabel="Emergency Guidance"
    >
      <Text style={{ fontSize: 22, fontWeight: "800", marginBottom: 8 }}>{strings.title}</Text>
      <Text style={{ fontSize: 14, color: "#475569", marginBottom: 16 }}>
        {strings.offline_notice}
      </Text>

      <View
        style={{
          backgroundColor: "#fee2e2",
          borderColor: "#ef4444",
          borderWidth: 1,
          borderRadius: 12,
          padding: 14,
          marginBottom: 16,
        }}
        testID="emergency-call-card"
      >
        <Text style={{ fontSize: 16, fontWeight: "700", marginBottom: 8 }}>{primary.label}</Text>
        <Text style={{ fontSize: 32, fontWeight: "900", marginBottom: 12, adjustsFontSizeToFit: true }}>{primary.number}</Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Call emergency services"
          onPress={() => openDial(primary.number)}
          style={{
            backgroundColor: "#ef4444",
            paddingVertical: 12,
            paddingHorizontal: 16,
            borderRadius: 10,
            alignSelf: "flex-start",
            minHeight: 44, // Ensure 44pt touch target
            minWidth: 100, // Wider for better text visibility
            justifyContent: 'center',
            alignItems: 'center',
          }}
          testID="call-emergency-button"
        >
          <Text style={{ color: "white", fontWeight: "800", fontSize: 16 }}>{strings.call_now}</Text>
        </Pressable>
        <Text style={{ fontSize: 12, color: "#991b1b", marginTop: 8 }}>
          {strings.dial_help}
        </Text>
      </View>

      {/* US Poison Control (static, offline) */}
      {showPoisonControl && (
        <View
          style={{
            backgroundColor: "#fef3c7",
            borderColor: "#f59e0b",
            borderWidth: 1,
            borderRadius: 12,
            padding: 14,
            marginBottom: 16,
          }}
          testID="poison-control-card"
        >
          <Text style={{ fontSize: 16, fontWeight: "700", marginBottom: 8 }}>{strings.poison_control}</Text>
          <Text style={{ fontSize: 24, fontWeight: "900", marginBottom: 12 }}>1-800-222-1222</Text>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Call poison control"
            onPress={() => openDial("18002221222")}
            style={{
              backgroundColor: "#f59e0b",
              paddingVertical: 12,
              paddingHorizontal: 16,
              borderRadius: 10,
              alignSelf: "flex-start",
              minHeight: 44,
              minWidth: 100,
              justifyContent: 'center',
              alignItems: 'center',
            }}
            testID="call-poison-control-button"
          >
            <Text style={{ color: "white", fontWeight: "800", fontSize: 16 }}>{strings.call_now}</Text>
          </Pressable>
        </View>
      )}

      <View style={{ gap: 12, marginBottom: 24 }}>
        <Text style={{ fontSize: 18, fontWeight: "700" }}>{strings.common_emergencies}</Text>
        <Text style={{ fontSize: 14 }}>{strings.choking}</Text>
        <Text style={{ fontSize: 14 }}>{strings.not_breathing}</Text>
        <Text style={{ fontSize: 14 }}>{strings.swallowed}</Text>
        <Text style={{ fontSize: 14 }}>{strings.allergic}</Text>
      </View>

      <View
        style={{
          backgroundColor: "#f1f5f9",
          borderRadius: 12,
          padding: 12,
        }}
      >
        <Text style={{ fontSize: 12, color: "#334155" }} testID="emergency-disclaimer">
          {strings.disclaimer}
        </Text>
      </View>
    </ScrollView>
  );
}
