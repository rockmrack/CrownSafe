/**
 * BabyShield Mobile API - TypeScript Type Definitions
 * 
 * Auto-generated from FastAPI backend OpenAPI schema
 * Last Updated: October 10, 2025
 * API Version: 1.0
 * 
 * Usage:
 * import type { User, Product, Recall, ScanResponse } from './babyshield-api-types';
 */

// ============================================
// AUTHENTICATION & USER TYPES
// ============================================

export interface User {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    phone?: string;
    profile?: UserProfile;
    subscription?: Subscription;
    statistics?: UserStatistics;
    created_at: string;
    updated_at: string;
}

export interface UserProfile {
    avatar_url?: string;
    notification_preferences: NotificationPreferences;
    privacy_settings: PrivacySettings;
}

export interface NotificationPreferences {
    email_alerts: boolean;
    push_notifications: boolean;
    sms_alerts: boolean;
}

export interface PrivacySettings {
    share_scan_history: boolean;
    anonymous_analytics: boolean;
}

export interface Subscription {
    tier: 'free' | 'premium' | 'family';
    status: 'active' | 'expired' | 'cancelled';
    expires_at?: string;
}

export interface UserStatistics {
    products_scanned: number;
    recalls_checked: number;
    alerts_received: number;
}

// ============================================
// AUTHENTICATION REQUESTS & RESPONSES
// ============================================

export interface RegisterRequest {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    phone?: string;
    accept_terms: boolean;
}

export interface LoginRequest {
    email: string;
    password: string;
}

export interface AuthResponse {
    access_token: string;
    refresh_token: string;
    token_type: 'bearer';
    expires_in: number;
    user?: User;
}

export interface RefreshTokenRequest {
    refresh_token: string;
}

export interface PasswordResetRequest {
    email: string;
}

export interface PasswordResetResponse {
    message: string;
    reset_token_expires_in: number;
}

// ============================================
// PRODUCT TYPES
// ============================================

export interface Product {
    id: string;
    name: string;
    brand: string;
    model_number?: string;
    category: string;
    image_url?: string;
    manufacturer?: string;
    description?: string;
    features?: string[];
    specifications?: Record<string, any>;
    safety_status: SafetyStatus;
    recalls: Recall[];
    created_at: string;
    updated_at: string;
}

export interface ProductSummary {
    id: string;
    name: string;
    brand: string;
    model_number?: string;
    category: string;
    image_url?: string;
    has_recalls: boolean;
    safety_score?: number;
}

export interface SafetyStatus {
    status: 'safe' | 'recalled' | 'warning' | 'unknown';
    recall_count: number;
    severity?: 'low' | 'medium' | 'high' | 'critical';
    last_checked: string;
    safety_score?: number;
    certifications?: string[];
}

// ============================================
// BARCODE & SCANNING TYPES
// ============================================

export interface ScanBarcodeRequest {
    barcode: string;
    barcode_type?: 'UPC-A' | 'UPC-E' | 'EAN-13' | 'EAN-8' | 'CODE-39' | 'CODE-128' | 'QR';
}

export interface ScanResponse {
    success: boolean;
    product?: Product;
    safety_status: SafetyStatus;
    recalls: Recall[];
    message?: string;
}

// ============================================
// RECALL TYPES
// ============================================

export interface Recall {
    id: string;
    title: string;
    description: string;
    product_name?: string;
    brand?: string;
    model_numbers?: string[];
    severity: 'low' | 'medium' | 'high' | 'critical';
    recall_date: string;
    agency: string;
    agency_country: string;
    affected_units?: number;
    injuries_reported?: number;
    deaths_reported?: number;
    remedy?: string;
    manufacturer_contact?: ManufacturerContact;
    url?: string;
    image_url?: string;
    created_at?: string;
    updated_at?: string;
}

export interface ManufacturerContact {
    phone?: string;
    email?: string;
    website?: string;
}

export interface RecallAlert {
    id: string;
    product: ProductSummary;
    recall: Recall;
    created_at: string;
    read: boolean;
    dismissed: boolean;
}

// ============================================
// SEARCH & PAGINATION TYPES
// ============================================

export interface SearchProductsParams {
    q: string;
    limit?: number;
    offset?: number;
    category?: string;
    has_recalls?: boolean;
}

export interface PaginatedResponse<T> {
    total: number;
    limit: number;
    offset: number;
    results: T[];
}

export type ProductSearchResponse = PaginatedResponse<ProductSummary>;
export type RecallSearchResponse = PaginatedResponse<Recall>;

// ============================================
// FAMILY MANAGEMENT TYPES
// ============================================

export interface FamilyMember {
    id: string;
    name: string;
    date_of_birth: string;
    age_months: number;
    relationship: 'son' | 'daughter' | 'other';
    avatar_url?: string;
    product_preferences?: ProductPreferences;
    created_at: string;
    updated_at?: string;
}

export interface ProductPreferences {
    age_appropriate_only: boolean;
    sensitivity_alerts?: string[];
}

export interface AddFamilyMemberRequest {
    name: string;
    date_of_birth: string;
    relationship: 'son' | 'daughter' | 'other';
    sensitivity_alerts?: string[];
}

// ============================================
// SAFETY REPORT TYPES
// ============================================

export interface SafetyReport {
    id: string;
    product_id: string;
    product?: ProductSummary;
    incident_type: 'injury' | 'defect' | 'near_miss' | 'quality_issue';
    severity: 'low' | 'medium' | 'high' | 'critical';
    description: string;
    incident_date: string;
    photos?: string[];
    status: 'submitted' | 'under_review' | 'resolved' | 'closed';
    reference_number: string;
    submitted_at: string;
    contact_manufacturer: boolean;
}

export interface SubmitSafetyReportRequest {
    product_id: string;
    incident_type: 'injury' | 'defect' | 'near_miss' | 'quality_issue';
    severity: 'low' | 'medium' | 'high' | 'critical';
    description: string;
    incident_date: string;
    photos?: string[];
    contact_manufacturer: boolean;
}

export interface SafetyReportResponse {
    id: string;
    status: 'submitted';
    reference_number: string;
    submitted_at: string;
    estimated_review_time: string;
}

// ============================================
// VISUAL RECOGNITION TYPES
// ============================================

export interface VisualAnalysisRequest {
    image: File | Blob;
    analysis_type: 'product_identification' | 'barcode_detection' | 'label_reading';
}

export interface VisualAnalysisResponse {
    status: 'completed' | 'processing' | 'failed';
    confidence: number;
    product?: ProductSummary;
    alternative_matches?: ProductMatch[];
    safety_check?: SafetyStatus;
    processing_time_ms?: number;
}

export interface ProductMatch {
    id: string;
    name: string;
    brand: string;
    confidence: number;
    image_url?: string;
}

// ============================================
// WATCH LIST TYPES
// ============================================

export interface WatchedProduct {
    id: string;
    product_id: string;
    user_id: string;
    notify_on_recall: boolean;
    notes?: string;
    created_at: string;
}

export interface AddToWatchListRequest {
    notify_on_recall: boolean;
    notes?: string;
}

// ============================================
// ERROR TYPES
// ============================================

export interface APIError {
    error: {
        code: string;
        message: string;
        details?: Record<string, any>;
        request_id?: string;
        timestamp?: string;
    };
}

export type ErrorCode =
    | 'INVALID_REQUEST'
    | 'UNAUTHORIZED'
    | 'FORBIDDEN'
    | 'NOT_FOUND'
    | 'CONFLICT'
    | 'VALIDATION_ERROR'
    | 'RATE_LIMIT_EXCEEDED'
    | 'INTERNAL_ERROR'
    | 'SERVICE_UNAVAILABLE'
    | 'INVALID_BARCODE'
    | 'PRODUCT_NOT_FOUND'
    | 'USER_NOT_FOUND';

// ============================================
// API CLIENT CONFIGURATION
// ============================================

export interface APIConfig {
    baseURL: string;
    timeout?: number;
    headers?: Record<string, string>;
}

export interface APIClientOptions {
    config: APIConfig;
    onTokenExpired?: () => Promise<string>;
    onError?: (error: APIError) => void;
}

// ============================================
// HTTP RESPONSE TYPES
// ============================================

export interface HTTPResponse<T = any> {
    data: T;
    status: number;
    statusText: string;
    headers: Record<string, string>;
}

export interface RateLimitHeaders {
    'x-ratelimit-limit': string;
    'x-ratelimit-remaining': string;
    'x-ratelimit-reset': string;
}

// ============================================
// UTILITY TYPES
// ============================================

export type DateString = string; // ISO 8601 format
export type URL = string;
export type EmailAddress = string;
export type PhoneNumber = string;
export type UUID = string;

// ============================================
// API ENDPOINT TYPES (for type-safe routing)
// ============================================

export interface APIEndpoints {
    // Authentication
    register: { method: 'POST'; path: '/api/v1/auth/register'; request: RegisterRequest; response: AuthResponse };
    login: { method: 'POST'; path: '/api/v1/auth/login'; request: LoginRequest; response: AuthResponse };
    refresh: { method: 'POST'; path: '/api/v1/auth/refresh'; request: RefreshTokenRequest; response: AuthResponse };
    passwordReset: { method: 'POST'; path: '/api/v1/auth/password-reset/request'; request: PasswordResetRequest; response: PasswordResetResponse };

    // Products
    searchProducts: { method: 'GET'; path: '/api/v1/products/search'; params: SearchProductsParams; response: ProductSearchResponse };
    getProduct: { method: 'GET'; path: '/api/v1/products/:id'; response: Product };
    scanBarcode: { method: 'POST'; path: '/api/v1/barcode/scan'; request: ScanBarcodeRequest; response: ScanResponse };

    // Recalls
    getActiveRecalls: { method: 'GET'; path: '/api/v1/recalls/active'; response: RecallSearchResponse };
    getUserAlerts: { method: 'GET'; path: '/api/v1/users/me/alerts'; response: { total_alerts: number; alerts: RecallAlert[] } };

    // User
    getCurrentUser: { method: 'GET'; path: '/api/v1/users/me'; response: User };
    updateUser: { method: 'PATCH'; path: '/api/v1/users/me'; request: Partial<User>; response: User };

    // Family
    getFamilyMembers: { method: 'GET'; path: '/api/v1/family/members'; response: { total: number; members: FamilyMember[] } };
    addFamilyMember: { method: 'POST'; path: '/api/v1/family/members'; request: AddFamilyMemberRequest; response: FamilyMember };

    // Safety Reports
    submitSafetyReport: { method: 'POST'; path: '/api/v1/safety-reports'; request: SubmitSafetyReportRequest; response: SafetyReportResponse };
    getUserReports: { method: 'GET'; path: '/api/v1/safety-reports/me'; response: { total: number; reports: SafetyReport[] } };

    // Visual Recognition
    analyzeImage: { method: 'POST'; path: '/api/v1/visual/analyze'; request: VisualAnalysisRequest; response: VisualAnalysisResponse };

    // Watch List
    addToWatchList: { method: 'POST'; path: '/api/v1/products/:id/watch'; request: AddToWatchListRequest; response: WatchedProduct };
}

// ============================================
// TYPE GUARDS
// ============================================

export function isAPIError(error: any): error is APIError {
    return error && typeof error === 'object' && 'error' in error && typeof error.error === 'object';
}

export function isRecalledProduct(product: Product): boolean {
    return product.safety_status.status === 'recalled' && product.safety_status.recall_count > 0;
}

export function isCriticalRecall(recall: Recall): boolean {
    return recall.severity === 'critical' || recall.severity === 'high';
}

// ============================================
// HELPER TYPES FOR FORMS
// ============================================

export type LoginFormData = Pick<LoginRequest, 'email' | 'password'>;
export type RegisterFormData = RegisterRequest;
export type UpdateProfileFormData = Pick<User, 'first_name' | 'last_name' | 'phone'> & {
    notification_preferences?: NotificationPreferences;
};

// ============================================
// EXPORT ALL
// ============================================

export type {
    // Re-export for convenience
    User as BabyShieldUser,
    Product as BabyShieldProduct,
    Recall as BabyShieldRecall,
    ScanResponse as BabyShieldScanResponse,
};
