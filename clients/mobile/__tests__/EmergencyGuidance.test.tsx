import React from "react";
import { render, fireEvent } from "@testing-library/react-native"; // @ts-ignore
import EmergencyGuidance from "../screens/EmergencyGuidance";

// Mock Linking module
const mockOpenURL = jest.fn();
jest.mock('react-native', () => ({
  ...jest.requireActual('react-native'),
  Linking: {
    openURL: mockOpenURL,
  },
}));

describe("EmergencyGuidance", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders and shows number for EU", () => {
    const { getByTestId, getByText } = render(
      <EmergencyGuidance route={{ params: { jurisdictionCode: "EU" } }} />
    );
    
    expect(getByTestId("emergency-guidance-screen")).toBeTruthy();
    expect(getByText("112")).toBeTruthy();
    expect(getByText("Local emergency")).toBeTruthy();
  });

  it("renders and shows number for US", () => {
    const { getByText } = render(
      <EmergencyGuidance route={{ params: { jurisdictionCode: "US" } }} />
    );
    
    expect(getByText("911")).toBeTruthy();
    expect(getByText("Local emergency")).toBeTruthy();
  });

  it("shows fallback pair when jurisdiction unknown", () => {
    const { getByText } = render(<EmergencyGuidance />);
    
    expect(getByText("112 / 911")).toBeTruthy();
    expect(getByText("Emergency (EU/US)")).toBeTruthy();
  });

  it("shows correct number for different jurisdictions", () => {
    const jurisdictions = [
      { code: "GB", expected: "999" },
      { code: "AU", expected: "000" },
      { code: "NZ", expected: "111" },
      { code: "CA", expected: "911" },
      { code: "IN", expected: "112" },
    ];

    jurisdictions.forEach(({ code, expected }) => {
      const { getByText } = render(
        <EmergencyGuidance route={{ params: { jurisdictionCode: code } }} />
      );
      expect(getByText(expected)).toBeTruthy();
    });
  });

  it("calls Linking.openURL when call button is pressed for single number", () => {
    const { getByTestId } = render(
      <EmergencyGuidance route={{ params: { jurisdictionCode: "EU" } }} />
    );
    
    const callButton = getByTestId("call-emergency-button");
    fireEvent.press(callButton);
    
    expect(mockOpenURL).toHaveBeenCalledWith("tel:112");
  });

  it("does not call Linking.openURL for fallback pair", () => {
    const { getByTestId } = render(<EmergencyGuidance />);
    
    const callButton = getByTestId("call-emergency-button");
    fireEvent.press(callButton);
    
    // Should not call openURL for "112 / 911" pair
    expect(mockOpenURL).not.toHaveBeenCalled();
  });

  it("handles Linking.openURL errors gracefully", () => {
    mockOpenURL.mockRejectedValue(new Error("Unable to open URL"));
    
    const { getByTestId } = render(
      <EmergencyGuidance route={{ params: { jurisdictionCode: "US" } }} />
    );
    
    const callButton = getByTestId("call-emergency-button");
    
    // Should not throw when Linking fails
    expect(() => fireEvent.press(callButton)).not.toThrow();
    expect(mockOpenURL).toHaveBeenCalledWith("tel:911");
  });

  it("contains all required emergency guidance content", () => {
    const { getByText, getByTestId } = render(<EmergencyGuidance />);
    
    // Header
    expect(getByText("🚨 Emergency Guidance")).toBeTruthy();
    
    // Offline notice
    expect(getByText(/This screen works offline/)).toBeTruthy();
    
    // Emergency scenarios
    expect(getByText(/Choking: Seek immediate help/)).toBeTruthy();
    expect(getByText(/Not breathing.*turning blue/)).toBeTruthy();
    expect(getByText(/Swallowed battery.*chemicals.*medicine/)).toBeTruthy();
    expect(getByText(/Severe allergic reaction/)).toBeTruthy();
    
    // Disclaimer
    expect(getByTestId("emergency-disclaimer")).toBeTruthy();
    expect(getByText(/BabyShield does not provide medical advice/)).toBeTruthy();
  });

  it("has proper accessibility properties", () => {
    const { getByTestId } = render(<EmergencyGuidance />);
    
    const screen = getByTestId("emergency-guidance-screen");
    expect(screen.props.accessibilityLabel).toBe("Emergency Guidance");
    
    const callButton = getByTestId("call-emergency-button");
    expect(callButton.props.accessibilityRole).toBe("button");
    expect(callButton.props.accessibilityLabel).toBe("Call emergency services");
  });

  it("has proper touch target size for call button", () => {
    const { getByTestId } = render(
      <EmergencyGuidance route={{ params: { jurisdictionCode: "EU" } }} />
    );
    
    const callButton = getByTestId("call-emergency-button");
    const buttonStyle = callButton.props.style;
    
    // Check that button meets 44pt minimum touch target
    expect(buttonStyle.minHeight).toBe(44);
    expect(buttonStyle.minWidth).toBe(44);
  });

  it("renders emergency call card with proper styling", () => {
    const { getByTestId } = render(<EmergencyGuidance />);
    
    const callCard = getByTestId("emergency-call-card");
    expect(callCard).toBeTruthy();
    
    const cardStyle = callCard.props.style;
    expect(cardStyle.backgroundColor).toBe("#fee2e2");
    expect(cardStyle.borderColor).toBe("#ef4444");
    expect(cardStyle.borderWidth).toBe(1);
  });

  it("handles missing route params gracefully", () => {
    const { getByText } = render(<EmergencyGuidance route={{}} />);
    
    // Should default to fallback numbers
    expect(getByText("112 / 911")).toBeTruthy();
    expect(getByText("Emergency (EU/US)")).toBeTruthy();
  });

  it("handles null route gracefully", () => {
    const { getByText } = render(<EmergencyGuidance route={null as any} />);
    
    // Should default to fallback numbers
    expect(getByText("112 / 911")).toBeTruthy();
    expect(getByText("Emergency (EU/US)")).toBeTruthy();
  });

  it("handles case insensitive jurisdiction codes", () => {
    const { getByText } = render(
      <EmergencyGuidance route={{ params: { jurisdictionCode: "eu" } }} />
    );
    
    expect(getByText("112")).toBeTruthy();
    expect(getByText("Local emergency")).toBeTruthy();
  });

  it("shows US Poison Control for US jurisdiction", () => {
    const { getByText, getByTestId } = render(
      <EmergencyGuidance route={{ params: { jurisdictionCode: "US" } }} />
    );
    
    expect(getByTestId("poison-control-card")).toBeTruthy();
    expect(getByText("Poison Control")).toBeTruthy();
    expect(getByText("1-800-222-1222")).toBeTruthy();
    expect(getByTestId("call-poison-control-button")).toBeTruthy();
  });

  it("does not show Poison Control for non-US jurisdictions", () => {
    const { queryByTestId } = render(
      <EmergencyGuidance route={{ params: { jurisdictionCode: "EU" } }} />
    );
    
    expect(queryByTestId("poison-control-card")).toBeNull();
  });

  it("calls poison control number when button is pressed", () => {
    const { getByTestId } = render(
      <EmergencyGuidance route={{ params: { jurisdictionCode: "US" } }} />
    );
    
    const poisonButton = getByTestId("call-poison-control-button");
    fireEvent.press(poisonButton);
    
    expect(mockOpenURL).toHaveBeenCalledWith("tel:18002221222");
  });

  it("renders in Spanish for ES jurisdiction", () => {
    const { getByText } = render(
      <EmergencyGuidance route={{ params: { jurisdictionCode: "ES" } }} />
    );
    
    expect(getByText("🚨 Guía de Emergencia")).toBeTruthy();
    expect(getByText("Llamar ahora")).toBeTruthy();
    expect(getByText(/Esta pantalla funciona sin conexión/)).toBeTruthy();
  });

  it("renders in Spanish for es locale", () => {
    const { getByText } = render(
      <EmergencyGuidance route={{ params: { locale: "es-ES" } }} />
    );
    
    expect(getByText("🚨 Guía de Emergencia")).toBeTruthy();
    expect(getByText("Llamar ahora")).toBeTruthy();
  });

  it("has proper font scaling for accessibility", () => {
    const { getByText } = render(
      <EmergencyGuidance route={{ params: { jurisdictionCode: "EU" } }} />
    );
    
    const numberText = getByText("112");
    // Check that adjustsFontSizeToFit is enabled for large text
    expect(numberText.props.adjustsFontSizeToFit).toBe(true);
  });

  it("handles airplane mode gracefully", () => {
    // Mock network unavailable
    mockOpenURL.mockRejectedValue(new Error("Network unavailable"));
    
    const { getByTestId } = render(
      <EmergencyGuidance route={{ params: { jurisdictionCode: "EU" } }} />
    );
    
    const callButton = getByTestId("call-emergency-button");
    
    // Should not crash in airplane mode
    expect(() => fireEvent.press(callButton)).not.toThrow();
  });
});
