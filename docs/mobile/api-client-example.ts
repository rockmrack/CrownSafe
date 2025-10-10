/**
 * BabyShield Mobile - Type-Safe API Client
 * 
 * Usage Example with TypeScript Types
 * Works with React Native, Expo, or any TypeScript mobile framework
 */

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type {
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    User,
    Product,
    ScanBarcodeRequest,
    ScanResponse,
    ProductSearchResponse,
    SearchProductsParams,
    RecallSearchResponse,
    APIError,
    FamilyMember,
    AddFamilyMemberRequest,
    SubmitSafetyReportRequest,
    SafetyReportResponse,
    AddToWatchListRequest,
    WatchedProduct,
} from './babyshield-api-types';

// ============================================
// CONFIGURATION
// ============================================

const API_CONFIG = {
    // Use environment variables for different environments
    baseURL: process.env.API_BASE_URL || 'https://babyshield.cureviax.ai',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
};

// Storage keys
const STORAGE_KEYS = {
    ACCESS_TOKEN: '@babyshield_access_token',
    REFRESH_TOKEN: '@babyshield_refresh_token',
    USER_DATA: '@babyshield_user_data',
};

// ============================================
// API CLIENT CLASS
// ============================================

class BabyShieldAPIClient {
    private client: AxiosInstance;
    private accessToken: string | null = null;
    private refreshToken: string | null = null;

    constructor() {
        this.client = axios.create(API_CONFIG);
        this.setupInterceptors();
        this.loadStoredTokens();
    }

    // ============================================
    // SETUP & INITIALIZATION
    // ============================================

    private setupInterceptors(): void {
        // Request interceptor - Add auth token
        this.client.interceptors.request.use(
            (config) => {
                if (this.accessToken) {
                    config.headers.Authorization = `Bearer ${this.accessToken}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        // Response interceptor - Handle token refresh
        this.client.interceptors.response.use(
            (response) => response,
            async (error: AxiosError<APIError>) => {
                const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

                // Handle 401 unauthorized - try to refresh token
                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;

                    try {
                        const newToken = await this.refreshAccessToken();
                        if (newToken && originalRequest.headers) {
                            originalRequest.headers.Authorization = `Bearer ${newToken}`;
                            return this.client(originalRequest);
                        }
                    } catch (refreshError) {
                        // Refresh failed - logout user
                        await this.logout();
                        throw refreshError;
                    }
                }

                // Handle rate limiting
                if (error.response?.status === 429) {
                    const retryAfter = error.response.headers['retry-after'];
                    if (retryAfter) {
                        await this.sleep(parseInt(retryAfter) * 1000);
                        return this.client(originalRequest);
                    }
                }

                return Promise.reject(this.handleError(error));
            }
        );
    }

    private async loadStoredTokens(): Promise<void> {
        try {
            const [accessToken, refreshToken] = await Promise.all([
                AsyncStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN),
                AsyncStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN),
            ]);
            this.accessToken = accessToken;
            this.refreshToken = refreshToken;
        } catch (error) {
            console.error('Failed to load stored tokens:', error);
        }
    }

    private async storeTokens(accessToken: string, refreshToken: string): Promise<void> {
        this.accessToken = accessToken;
        this.refreshToken = refreshToken;
        await Promise.all([
            AsyncStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken),
            AsyncStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken),
        ]);
    }

    private async clearTokens(): Promise<void> {
        this.accessToken = null;
        this.refreshToken = null;
        await Promise.all([
            AsyncStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN),
            AsyncStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN),
            AsyncStorage.removeItem(STORAGE_KEYS.USER_DATA),
        ]);
    }

    // ============================================
    // AUTHENTICATION
    // ============================================

    async register(data: RegisterRequest): Promise<AuthResponse> {
        const response = await this.client.post<AuthResponse>('/api/v1/auth/register', data);
        await this.storeTokens(response.data.access_token, response.data.refresh_token);
        if (response.data.user) {
            await AsyncStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(response.data.user));
        }
        return response.data;
    }

    async login(data: LoginRequest): Promise<AuthResponse> {
        const response = await this.client.post<AuthResponse>('/api/v1/auth/login', data);
        await this.storeTokens(response.data.access_token, response.data.refresh_token);
        if (response.data.user) {
            await AsyncStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(response.data.user));
        }
        return response.data;
    }

    async logout(): Promise<void> {
        await this.clearTokens();
    }

    async refreshAccessToken(): Promise<string | null> {
        if (!this.refreshToken) {
            throw new Error('No refresh token available');
        }

        try {
            const response = await this.client.post<AuthResponse>('/api/v1/auth/refresh', {
                refresh_token: this.refreshToken,
            });
            await this.storeTokens(response.data.access_token, this.refreshToken);
            return response.data.access_token;
        } catch (error) {
            await this.clearTokens();
            return null;
        }
    }

    async requestPasswordReset(email: string): Promise<void> {
        await this.client.post('/api/v1/auth/password-reset/request', { email });
    }

    // ============================================
    // PRODUCTS & BARCODE
    // ============================================

    async scanBarcode(data: ScanBarcodeRequest): Promise<ScanResponse> {
        const response = await this.client.post<ScanResponse>('/api/v1/barcode/scan', data);
        return response.data;
    }

    async searchProducts(params: SearchProductsParams): Promise<ProductSearchResponse> {
        const response = await this.client.get<ProductSearchResponse>('/api/v1/products/search', {
            params,
        });
        return response.data;
    }

    async getProduct(productId: string): Promise<Product> {
        const response = await this.client.get<Product>(`/api/v1/products/${productId}`);
        return response.data;
    }

    // ============================================
    // RECALLS
    // ============================================

    async getActiveRecalls(params?: {
        limit?: number;
        offset?: number;
        category?: string;
        severity?: string;
    }): Promise<RecallSearchResponse> {
        const response = await this.client.get<RecallSearchResponse>('/api/v1/recalls/active', {
            params,
        });
        return response.data;
    }

    async getUserAlerts() {
        const response = await this.client.get('/api/v1/users/me/alerts');
        return response.data;
    }

    // ============================================
    // USER PROFILE
    // ============================================

    async getCurrentUser(): Promise<User> {
        const response = await this.client.get<User>('/api/v1/users/me');
        await AsyncStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(response.data));
        return response.data;
    }

    async updateUser(data: Partial<User>): Promise<User> {
        const response = await this.client.patch<User>('/api/v1/users/me', data);
        await AsyncStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(response.data));
        return response.data;
    }

    async getCachedUser(): Promise<User | null> {
        const cached = await AsyncStorage.getItem(STORAGE_KEYS.USER_DATA);
        return cached ? JSON.parse(cached) : null;
    }

    // ============================================
    // FAMILY MANAGEMENT
    // ============================================

    async getFamilyMembers(): Promise<{ total: number; members: FamilyMember[] }> {
        const response = await this.client.get('/api/v1/family/members');
        return response.data;
    }

    async addFamilyMember(data: AddFamilyMemberRequest): Promise<FamilyMember> {
        const response = await this.client.post<FamilyMember>('/api/v1/family/members', data);
        return response.data;
    }

    async updateFamilyMember(memberId: string, data: Partial<AddFamilyMemberRequest>): Promise<FamilyMember> {
        const response = await this.client.patch<FamilyMember>(`/api/v1/family/members/${memberId}`, data);
        return response.data;
    }

    async deleteFamilyMember(memberId: string): Promise<void> {
        await this.client.delete(`/api/v1/family/members/${memberId}`);
    }

    // ============================================
    // SAFETY REPORTS
    // ============================================

    async submitSafetyReport(data: SubmitSafetyReportRequest): Promise<SafetyReportResponse> {
        const response = await this.client.post<SafetyReportResponse>('/api/v1/safety-reports', data);
        return response.data;
    }

    async getUserSafetyReports() {
        const response = await this.client.get('/api/v1/safety-reports/me');
        return response.data;
    }

    // ============================================
    // WATCH LIST
    // ============================================

    async addToWatchList(productId: string, data: AddToWatchListRequest): Promise<WatchedProduct> {
        const response = await this.client.post<WatchedProduct>(
            `/api/v1/products/${productId}/watch`,
            data
        );
        return response.data;
    }

    async removeFromWatchList(productId: string): Promise<void> {
        await this.client.delete(`/api/v1/products/${productId}/watch`);
    }

    async getWatchList() {
        const response = await this.client.get('/api/v1/products/watchlist');
        return response.data;
    }

    // ============================================
    // VISUAL RECOGNITION
    // ============================================

    async analyzeImage(imageFile: File | Blob): Promise<any> {
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('analysis_type', 'product_identification');

        const response = await this.client.post('/api/v1/visual/analyze', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    }

    // ============================================
    // UTILITY METHODS
    // ============================================

    isAuthenticated(): boolean {
        return this.accessToken !== null;
    }

    private handleError(error: AxiosError<APIError>): Error {
        if (error.response?.data?.error) {
            const apiError = error.response.data.error;
            return new Error(`${apiError.code}: ${apiError.message}`);
        }
        return error;
    }

    private sleep(ms: number): Promise<void> {
        return new Promise((resolve) => setTimeout(resolve, ms));
    }
}

// ============================================
// SINGLETON INSTANCE
// ============================================

const apiClient = new BabyShieldAPIClient();
export default apiClient;

// ============================================
// EXPORT TYPES FOR CONVENIENCE
// ============================================

export type { BabyShieldAPIClient };
export * from './babyshield-api-types';

// ============================================
// USAGE EXAMPLES
// ============================================

/**
 * Example 1: Login
 * 
 * import apiClient from './api-client';
 * 
 * const handleLogin = async (email: string, password: string) => {
 *   try {
 *     const response = await apiClient.login({ email, password });
 *     console.log('Logged in:', response.user);
 *   } catch (error) {
 *     console.error('Login failed:', error);
 *   }
 * };
 */

/**
 * Example 2: Scan Barcode
 * 
 * const handleBarcodeScan = async (barcode: string) => {
 *   try {
 *     const result = await apiClient.scanBarcode({ barcode });
 *     if (result.success && result.product) {
 *       console.log('Product found:', result.product.name);
 *       if (result.safety_status.status === 'recalled') {
 *         console.warn('⚠️ RECALLED PRODUCT!');
 *       }
 *     }
 *   } catch (error) {
 *     console.error('Scan failed:', error);
 *   }
 * };
 */

/**
 * Example 3: Search Products
 * 
 * const searchProducts = async (query: string) => {
 *   try {
 *     const results = await apiClient.searchProducts({
 *       q: query,
 *       limit: 20,
 *       offset: 0
 *     });
 *     console.log(`Found ${results.total} products`);
 *     return results.results;
 *   } catch (error) {
 *     console.error('Search failed:', error);
 *     return [];
 *   }
 * };
 */

/**
 * Example 4: Get User Profile
 * 
 * const loadUserProfile = async () => {
 *   try {
 *     // Try to get cached data first (faster)
 *     const cached = await apiClient.getCachedUser();
 *     if (cached) return cached;
 *     
 *     // Fetch from API if no cache
 *     const user = await apiClient.getCurrentUser();
 *     return user;
 *   } catch (error) {
 *     console.error('Failed to load profile:', error);
 *     return null;
 *   }
 * };
 */

/**
 * Example 5: Check Authentication
 * 
 * const checkAuth = () => {
 *   if (!apiClient.isAuthenticated()) {
 *     // Navigate to login screen
 *     navigation.navigate('Login');
 *   }
 * };
 */
