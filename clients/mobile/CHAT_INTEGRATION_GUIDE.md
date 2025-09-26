# BabyShield Mobile Integration Guide

## Overview

The BabyShield mobile components provide a complete scan result experience with:
- **Safety Verdict Card**: Traffic-light style visual feedback (safe/caution/recall)
- **Chat Feature**: AI-powered explanations of scan results in parent-friendly language
- **Interactive ChatBox**: Full conversation UI with smart chips and emergency guidance

This guide shows how to integrate these components into your existing React Native app.

## Quick Start

### 1. Import the Components

```tsx
import { VerdictCard, ExplainResultButton, ChatBox } from "./components";
import { mapScanToVerdict } from "./utils";
```

### 2. Complete Scan Result Screen

```tsx
import { ScanResultScreen } from "./screens";

// Use the complete screen component
<ScanResultScreen
  scanId={yourScanId}
  scanData={yourScanData}
  apiBase={process.env.EXPO_PUBLIC_API_BASE as string}
  productName="Example Product"
  barcode="1234567890"
  onFeedback={(helpful) => {
    Analytics.track("explain_result_feedback", { scanId: yourScanId, helpful });
  }}
/>
```

### 3. Or Build Your Own Layout

```tsx
// Map your scan data to verdict
const mapped = mapScanToVerdict({
  recalls_found: scanData.recall_count,
  key_flags: scanData.flags,
  one_line_reason: scanData.reason
});

// Render verdict card at top
<VerdictCard
  verdict={mapped.verdict}
  oneLine={mapped.oneLine}
  flags={mapped.flags}
  onExplain={() => {/* handled by ExplainResultButton */}}
  onSetAlert={() => {/* wire to alert system */}}
/>

// Render explain button below
<ExplainResultButton 
  baseUrl={process.env.EXPO_PUBLIC_API_BASE as string}
  scanId={yourScanId}
  onFeedback={(helpful) => {
    Analytics.track("explain_result_feedback", { scanId: yourScanId, helpful });
  }}
/>

// Add interactive chat box
<ChatBox
  apiBase={process.env.EXPO_PUBLIC_API_BASE as string}
  scanId={yourScanId}
  smartChips={["Pregnancy risk?", "Allergies?", "Recall details"]}
/>
```

### 4. Environment Setup

Ensure your `.env` file includes:

```
EXPO_PUBLIC_API_BASE=https://babyshield.cureviax.ai
```

## Component APIs

### VerdictCard Props

| Prop | Type | Description |
|------|------|-------------|
| `verdict` | `"safe" \| "caution" \| "avoid" \| "recall"` | Safety verdict level |
| `oneLine` | `string` | Short reason, one sentence |
| `flags?` | `string[]` | Optional flags (e.g., `["contains_peanuts"]`) |
| `onExplain?` | `() => void` | Optional callback for explain button |
| `onSetAlert?` | `() => void` | Optional callback for alert button |

### ExplainResultButton Props

| Prop | Type | Description |
|------|------|-------------|
| `baseUrl` | `string` | API base URL (e.g., `https://babyshield.cureviax.ai`) |
| `scanId` | `string` | The scan ID to explain |
| `onFeedback?` | `(helpful: boolean) => void` | Optional callback for user feedback |

### ChatBox Props

| Prop | Type | Description |
|------|------|-------------|
| `apiBase` | `string` | API base URL (e.g., `https://babyshield.cureviax.ai`) |
| `scanId` | `string` | The scan ID to discuss |
| `smartChips?` | `string[]` | Optional quick-action chips (default: pregnancy, allergies, alternatives) |

### ExplanationResponse Type

```tsx
type ExplanationResponse = {
  summary: string;      // 2-3 line plain-language explanation
  reasons: string[];    // Bulleted reasons behind the verdict
  checks: string[];     // Concrete checks for the user to perform
  flags: string[];      // Machine-readable tags
  disclaimer: string;   // Short non-diagnostic disclaimer
};
```

## Error Handling

The component automatically handles:
- Network errors → Alert dialog
- API errors → Alert with error message
- Loading states → Activity indicator
- Modal dismissal → Clean state reset

## Acceptance Criteria ✅

### Task 0.3 - Chat Feature
- [x] Tapping the button calls `POST /api/v1/chat/explain-result` with the current `scan_id`
- [x] The modal shows `summary`, `reasons`, `checks`, `flags`, `disclaimer`
- [x] Errors surface as an alert; UI never freezes
- [x] 👍/👎 emits a client analytics event (server endpoint to be added later)

### Task 1.1 - Verdict Card
- [x] The Scan Result screen renders a **non-interactive Verdict Card at the top**
- [x] Traffic-light style (emoji/colors), one-line reason, and flags
- [x] The existing **Explain** flow remains available (button right below the card)
- [x] No backend changes required; consumes existing `scanData`
- [x] Test IDs present: `verdict-card`, `btn-explain`

### Task 1.4 - Interactive ChatBox
- [x] Typing a question hits `POST /api/v1/chat/conversation`
- [x] Assistant messages render `summary`, `reasons`, `checks`, `flags`, `disclaimer`
- [x] Emergency strip visible above chat
- [x] Conversation ID persists across messages
- [x] Smart chips for common questions
- [x] Full conversation UI with proper styling

## Example Integration

See `ScanResultScreen.example.tsx` for a complete example of how to integrate the chat feature into your existing scan result display.

## Future Enhancements

- Server-side feedback endpoint (Task 1.x)
- Conversation history
- Multi-language support
- Voice input/output
- Push notifications for follow-up advice
