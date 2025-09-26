/**
 * BabyShield API Client for React Native / Mobile Web
 * @version 1.2.0
 * @description TypeScript client for BabyShield recall search API
 */

// Type definitions
export type Severity = "low" | "medium" | "high" | "critical";
export type RiskCategory = "drug" | "device" | "food" | "cosmetic" | "supplement" | "toy" | "baby_product" | "other";
export type RecallStatus = "open" | "closed";

export interface RecallItem {
  // Required fields
  id: string;
  agencyCode: string;
  title: string;
  recallDate: string; // YYYY-MM-DD
  
  // Optional fields
  productName?: string;
  brand?: string;
  manufacturer?: string;
  model?: string;
  modelNumber?: string;
  upc?: string;
  hazard?: string;
  riskCategory?: RiskCategory;
  severity?: Severity;
  status?: RecallStatus;
  imageUrl?: string | null;
  affectedCountries?: string[];
  country?: string;
  lastUpdated?: string; // ISO 8601
  sourceUrl?: string;
  description?: string;
  url?: string;
  relevanceScore?: number; // 0-1 for fuzzy match results
}

export interface AdvancedSearchRequest {
  // Text search (at least one required unless using filters only)
  query?: string;           // Free text search
  product?: string;         // Product search (preferred)
  keywords?: string[];      // AND logic - all must match
  id?: string;             // Exact ID lookup
  
  // Filters
  agencies?: string[];      // e.g., ["FDA", "CPSC"]
  agency?: string;         // Single agency (alias for agencies)
  severity?: Severity;
  risk_level?: string;     // Alias for severity
  riskCategory?: RiskCategory;
  product_category?: string; // Alias for riskCategory
  date_from?: string;      // YYYY-MM-DD
  date_to?: string;        // YYYY-MM-DD
  
  // Pagination
  limit?: number;          // 1-50, default 20
  nextCursor?: string | null;
}

export interface AdvancedSearchResponse {
  ok: boolean;
  data: {
    items: RecallItem[];
    nextCursor?: string | null;
    total?: number;
    limit?: number;
    offset?: number;
  };
  traceId: string;
  responseTimeMs?: number;
}

export interface RecallDetailResponse {
  ok: boolean;
  data: RecallItem;
  traceId?: string;
}

export interface ErrorResponse {
  ok: false;
  error: {
    code: string;
    message: string;
    unknown?: string[];
  };
  traceId: string;
}

export interface HealthResponse {
  ok: boolean;
  status: string;
  timestamp: string;
  version: string;
  service: string;
}

export interface AgenciesResponse {
  ok: boolean;
  data: {
    agencies: string[];
  };
}

export interface EvidenceItem {
  type: "recall" | "regulation" | "guideline" | "datasheet" | "label";
  source: string;
  id?: string;
  url?: string;
}

export interface AlternativeItem {
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
  evidence: EvidenceItem[];
}

export interface EmergencyNotice {
  level: "red" | "amber";
  reason: string;
  cta: string;
}

export interface ExplanationResponse {
  summary: string;
  reasons: string[];
  checks: string[];
  flags: string[];
  disclaimer: string;
  jurisdiction?: { code?: string; label?: string };
  evidence?: EvidenceItem[];
  alternatives?: {
    items: AlternativeItem[];
  };
  suggested_questions?: string[];
  emergency?: EmergencyNotice;
}

export interface ExplainRequest {
  scan_id: string;
}

export type Intent = 
  | "pregnancy_risk"
  | "allergy_question"
  | "ingredient_info"
  | "age_appropriateness"
  | "alternative_products"
  | "recall_details"
  | "unclear_intent";

/**
 * BabyShield API Client
 * 
 * @example
 * ```typescript
 * const api = new BabyShieldClient();
 * 
 * // Fuzzy product search
 * const results = await api.searchAdvanced({
 *   product: "pacifier",
 *   agencies: ["FDA"],
 *   limit: 5
 * });
 * 
 * // Keyword search with AND logic
 * const results2 = await api.searchAdvanced({
 *   keywords: ["baby", "formula"],
 *   severity: "high"
 * });
 * 
 * // Get specific recall
 * const recall = await api.getRecallById("2024-FDA-12345");
 * 
 * // Explain a scan result
 * const explanation = await api.explainResult("scan_12345");
 * console.log(explanation.summary);
 * ```
 */
export class BabyShieldClient {
  private readonly base: string;
  private readonly headers: HeadersInit;
  
  constructor(base = "https://babyshield.cureviax.ai", apiKey?: string) {
    this.base = base;
    this.headers = {
      "Content-Type": "application/json",
      ...(apiKey && { "X-API-Key": apiKey })
    };
  }
  
  /**
   * Advanced search with fuzzy matching, keywords, and filters
   */
  async searchAdvanced(req: AdvancedSearchRequest): Promise<AdvancedSearchResponse> {
    const response = await fetch(`${this.base}/api/v1/search/advanced`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify(req),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new BabyShieldError(
        data.error?.message || `Search failed: ${response.status}`,
        data.error?.code || "SEARCH_ERROR",
        response.status,
        data.traceId
      );
    }
    
    return data as AdvancedSearchResponse;
  }
  
  /**
   * Get detailed information for a specific recall
   */
  async getRecallById(id: string): Promise<RecallItem> {
    const response = await fetch(
      `${this.base}/api/v1/recall/${encodeURIComponent(id)}`,
      { headers: this.headers }
    );
    
    const data = await response.json();
    
    if (response.status === 404) {
      throw new BabyShieldError(
        `Recall not found: ${id}`,
        "NOT_FOUND",
        404,
        data.traceId
      );
    }
    
    if (!response.ok) {
      throw new BabyShieldError(
        data.error?.message || `Failed to get recall: ${response.status}`,
        data.error?.code || "RECALL_ERROR",
        response.status,
        data.traceId
      );
    }
    
    // Handle both direct RecallItem and wrapped response
    return data.data || data;
  }
  
  /**
   * Quick FDA search (simple GET endpoint)
   */
  async searchFDA(product: string, limit = 20): Promise<AdvancedSearchResponse> {
    const params = new URLSearchParams({
      product,
      limit: limit.toString(),
    });
    
    const response = await fetch(
      `${this.base}/api/v1/fda?${params}`,
      { headers: this.headers }
    );
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new BabyShieldError(
        data.error?.message || `FDA search failed: ${response.status}`,
        data.error?.code || "FDA_SEARCH_ERROR",
        response.status,
        data.traceId
      );
    }
    
    return data as AdvancedSearchResponse;
  }
  
  /**
   * Health check endpoint
   */
  async healthCheck(): Promise<HealthResponse> {
    const response = await fetch(
      `${this.base}/api/v1/healthz`,
      { headers: this.headers }
    );
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new BabyShieldError(
        "Health check failed",
        "HEALTH_CHECK_ERROR",
        response.status
      );
    }
    
    return data as HealthResponse;
  }
  
  /**
   * Get list of available agencies
   */
  async getAgencies(): Promise<string[]> {
    const response = await fetch(
      `${this.base}/api/v1/agencies`,
      { headers: this.headers }
    );
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new BabyShieldError(
        "Failed to get agencies",
        "AGENCIES_ERROR",
        response.status
      );
    }
    
    return data.data?.agencies || [];
  }
  
  /**
   * Explain a scan result in parent-friendly language
   */
  async explainResult(scanId: string): Promise<ExplanationResponse> {
    const response = await fetch(
      `${this.base}/api/v1/chat/explain-result`,
      {
        method: "POST",
        headers: this.headers,
        body: JSON.stringify({ scan_id: scanId }),
      }
    );
    
    const data = await response.json();
    
    if (response.status === 404) {
      throw new BabyShieldError(
        `Scan not found: ${scanId}`,
        "SCAN_NOT_FOUND",
        404,
        data.traceId
      );
    }
    
    if (!response.ok) {
      throw new BabyShieldError(
        data.error?.message || `Failed to explain result: ${response.status}`,
        data.error?.code || "EXPLAIN_ERROR",
        response.status,
        data.traceId
      );
    }
    
    return data as ExplanationResponse;
  }
  
  /**
   * Build a search request with proper validation
   */
  buildSearchRequest(params: Partial<AdvancedSearchRequest>): AdvancedSearchRequest {
    const request: AdvancedSearchRequest = {};
    
    // Copy valid fields
    if (params.product) request.product = params.product;
    if (params.query) request.query = params.query;
    if (params.keywords && params.keywords.length > 0) {
      request.keywords = params.keywords;
    }
    if (params.id) request.id = params.id;
    
    // Handle agency/agencies
    if (params.agencies) {
      request.agencies = params.agencies;
    } else if (params.agency) {
      request.agencies = [params.agency];
    }
    
    // Handle severity/risk_level
    if (params.severity) {
      request.severity = params.severity;
    } else if (params.risk_level) {
      request.severity = params.risk_level as Severity;
    }
    
    // Handle riskCategory/product_category
    if (params.riskCategory) {
      request.riskCategory = params.riskCategory;
    } else if (params.product_category) {
      request.riskCategory = params.product_category as RiskCategory;
    }
    
    // Date filters
    if (params.date_from) request.date_from = params.date_from;
    if (params.date_to) request.date_to = params.date_to;
    
    // Pagination
    if (params.limit) {
      request.limit = Math.min(Math.max(1, params.limit), 50);
    }
    if (params.nextCursor !== undefined) {
      request.nextCursor = params.nextCursor;
    }
    
    return request;
  }

  /**
   * Record when a user clicks on an alternative product suggestion
   */
  async recordAlternativeClick(scanId: string, altId: string): Promise<void> {
    try {
      const response = await fetch(
        `${this.base}/api/v1/analytics/alt-click`,
        {
          method: "POST",
          headers: this.headers,
          body: JSON.stringify({
            scan_id: scanId,
            alt_id: altId,
          }),
        }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      // Non-blocking: log but don't throw
      console.warn("Failed to record alternative click:", error);
    }
  }
}

/**
 * Custom error class for BabyShield API errors
 */
export class BabyShieldError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly status: number,
    public readonly traceId?: string
  ) {
    super(message);
    this.name = "BabyShieldError";
  }
}

/**
 * Helper function to format recall date
 */
export function formatRecallDate(dateStr: string): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric"
  });
}

/**
 * Helper function to get severity color for UI
 */
export function getSeverityColor(severity?: Severity): string {
  switch (severity) {
    case "critical":
      return "#8B0000"; // Dark red
    case "high":
      return "#FF0000"; // Red
    case "medium":
      return "#FFA500"; // Orange
    case "low":
      return "#FFD700"; // Gold
    default:
      return "#808080"; // Gray
  }
}

/**
 * Helper function to check if recall is recent (within N days)
 */
export function isRecentRecall(recallDate: string, days = 30): boolean {
  const recall = new Date(recallDate);
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  return recall >= cutoff;
}

// Default export
export default BabyShieldClient;
