//
//  BabyShieldClient.swift
//  BabyShield API Client for iOS
//
//  Version: 1.2.0
//  Copyright © 2025 BabyShield. All rights reserved.
//

import Foundation

// MARK: - Data Models

enum Severity: String, Codable {
    case low = "low"
    case medium = "medium"
    case high = "high"
    case critical = "critical"
}

enum RiskCategory: String, Codable {
    case drug = "drug"
    case device = "device"
    case food = "food"
    case cosmetic = "cosmetic"
    case supplement = "supplement"
    case toy = "toy"
    case babyProduct = "baby_product"
    case other = "other"
}

enum RecallStatus: String, Codable {
    case open = "open"
    case closed = "closed"
}

struct RecallItem: Codable {
    let id: String
    let agencyCode: String
    let title: String
    let recallDate: String
    
    let productName: String?
    let brand: String?
    let manufacturer: String?
    let model: String?
    let modelNumber: String?
    let upc: String?
    let hazard: String?
    let riskCategory: RiskCategory?
    let severity: Severity?
    let status: RecallStatus?
    let imageUrl: String?
    let affectedCountries: [String]?
    let country: String?
    let lastUpdated: String?
    let sourceUrl: String?
    let description: String?
    let url: String?
    let relevanceScore: Double?
}

struct SearchData: Codable {
    let items: [RecallItem]
    let nextCursor: String?
    let total: Int?
    let limit: Int?
    let offset: Int?
}

struct SearchResponse: Codable {
    let ok: Bool
    let data: SearchData
    let traceId: String
    let responseTimeMs: Double?
}

struct RecallDetailResponse: Codable {
    let ok: Bool
    let data: RecallItem
    let traceId: String?
}

struct ErrorData: Codable {
    let code: String
    let message: String
    let unknown: [String]?
}

struct ErrorResponse: Codable {
    let ok: Bool
    let error: ErrorData
    let traceId: String
}

struct HealthResponse: Codable {
    let ok: Bool
    let status: String
    let timestamp: String
    let version: String
    let service: String
}

struct AgenciesData: Codable {
    let agencies: [String]
}

struct AgenciesResponse: Codable {
    let ok: Bool
    let data: AgenciesData
}

// MARK: - API Client

/// BabyShield API Client for iOS
///
/// Example usage:
/// ```swift
/// let client = BabyShieldClient()
///
/// // Fuzzy product search
/// let searchRequest = [
///     "product": "pacifier",
///     "agencies": ["FDA"],
///     "limit": 5
/// ]
/// let results = try await client.searchAdvanced(searchRequest)
///
/// // Get specific recall
/// let recall = try await client.getRecallById("2024-FDA-12345")
/// ```
final class BabyShieldClient {
    private let base: String
    private let session: URLSession
    private var apiKey: String?
    
    enum APIError: LocalizedError {
        case invalidURL
        case noData
        case decodingError
        case serverError(code: String, message: String, traceId: String?)
        case networkError(Error)
        case notFound(id: String)
        
        var errorDescription: String? {
            switch self {
            case .invalidURL:
                return "Invalid URL"
            case .noData:
                return "No data received"
            case .decodingError:
                return "Failed to decode response"
            case .serverError(_, let message, _):
                return message
            case .networkError(let error):
                return error.localizedDescription
            case .notFound(let id):
                return "Recall not found: \(id)"
            }
        }
    }
    
    init(base: String = "https://babyshield.cureviax.ai", apiKey: String? = nil) {
        self.base = base
        self.apiKey = apiKey
        
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)
    }
    
    // MARK: - Public Methods
    
    /// Advanced search with fuzzy matching and filters
    func searchAdvanced(_ payload: [String: Any]) async throws -> SearchResponse {
        guard let url = URL(string: "\(base)/api/v1/search/advanced") else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        if let apiKey = apiKey {
            request.addValue(apiKey, forHTTPHeaderField: "X-API-Key")
        }
        
        request.httpBody = try JSONSerialization.data(withJSONObject: payload, options: [])
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.noData
        }
        
        if httpResponse.statusCode != 200 {
            if let errorResponse = try? JSONDecoder().decode(ErrorResponse.self, from: data) {
                throw APIError.serverError(
                    code: errorResponse.error.code,
                    message: errorResponse.error.message,
                    traceId: errorResponse.traceId
                )
            }
            throw APIError.serverError(
                code: "HTTP_\(httpResponse.statusCode)",
                message: "Request failed with status \(httpResponse.statusCode)",
                traceId: nil
            )
        }
        
        guard let searchResponse = try? JSONDecoder().decode(SearchResponse.self, from: data) else {
            throw APIError.decodingError
        }
        
        return searchResponse
    }
    
    /// Get recall by ID
    func getRecallById(_ id: String) async throws -> RecallItem {
        guard let encodedId = id.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed),
              let url = URL(string: "\(base)/api/v1/recall/\(encodedId)") else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        if let apiKey = apiKey {
            request.addValue(apiKey, forHTTPHeaderField: "X-API-Key")
        }
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.noData
        }
        
        if httpResponse.statusCode == 404 {
            throw APIError.notFound(id: id)
        }
        
        if httpResponse.statusCode != 200 {
            if let errorResponse = try? JSONDecoder().decode(ErrorResponse.self, from: data) {
                throw APIError.serverError(
                    code: errorResponse.error.code,
                    message: errorResponse.error.message,
                    traceId: errorResponse.traceId
                )
            }
            throw APIError.serverError(
                code: "HTTP_\(httpResponse.statusCode)",
                message: "Request failed with status \(httpResponse.statusCode)",
                traceId: nil
            )
        }
        
        // Try to decode as RecallDetailResponse first
        if let detailResponse = try? JSONDecoder().decode(RecallDetailResponse.self, from: data) {
            return detailResponse.data
        }
        
        // Fall back to direct RecallItem
        guard let recall = try? JSONDecoder().decode(RecallItem.self, from: data) else {
            throw APIError.decodingError
        }
        
        return recall
    }
    
    /// FDA quick search
    func searchFDA(product: String, limit: Int = 20) async throws -> SearchResponse {
        var components = URLComponents(string: "\(base)/api/v1/fda")
        components?.queryItems = [
            URLQueryItem(name: "product", value: product),
            URLQueryItem(name: "limit", value: String(limit))
        ]
        
        guard let url = components?.url else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        if let apiKey = apiKey {
            request.addValue(apiKey, forHTTPHeaderField: "X-API-Key")
        }
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.noData
        }
        
        if httpResponse.statusCode != 200 {
            if let errorResponse = try? JSONDecoder().decode(ErrorResponse.self, from: data) {
                throw APIError.serverError(
                    code: errorResponse.error.code,
                    message: errorResponse.error.message,
                    traceId: errorResponse.traceId
                )
            }
            throw APIError.serverError(
                code: "HTTP_\(httpResponse.statusCode)",
                message: "Request failed with status \(httpResponse.statusCode)",
                traceId: nil
            )
        }
        
        guard let searchResponse = try? JSONDecoder().decode(SearchResponse.self, from: data) else {
            throw APIError.decodingError
        }
        
        return searchResponse
    }
    
    /// Health check
    func healthCheck() async throws -> HealthResponse {
        guard let url = URL(string: "\(base)/api/v1/healthz") else {
            throw APIError.invalidURL
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.serverError(
                code: "HEALTH_CHECK_FAILED",
                message: "Health check failed",
                traceId: nil
            )
        }
        
        guard let healthResponse = try? JSONDecoder().decode(HealthResponse.self, from: data) else {
            throw APIError.decodingError
        }
        
        return healthResponse
    }
    
    /// Get available agencies
    func getAgencies() async throws -> [String] {
        guard let url = URL(string: "\(base)/api/v1/agencies") else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        if let apiKey = apiKey {
            request.addValue(apiKey, forHTTPHeaderField: "X-API-Key")
        }
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.serverError(
                code: "AGENCIES_FAILED",
                message: "Failed to get agencies",
                traceId: nil
            )
        }
        
        guard let agenciesResponse = try? JSONDecoder().decode(AgenciesResponse.self, from: data) else {
            throw APIError.decodingError
        }
        
        return agenciesResponse.data.agencies
    }
    
    // MARK: - Helper Methods
    
    /// Build a properly formatted search request dictionary
    func buildSearchRequest(
        product: String? = nil,
        query: String? = nil,
        keywords: [String]? = nil,
        id: String? = nil,
        agencies: [String]? = nil,
        severity: Severity? = nil,
        riskCategory: RiskCategory? = nil,
        dateFrom: Date? = nil,
        dateTo: Date? = nil,
        limit: Int? = nil
    ) -> [String: Any] {
        var request: [String: Any] = [:]
        
        if let product = product {
            request["product"] = product
        }
        if let query = query {
            request["query"] = query
        }
        if let keywords = keywords, !keywords.isEmpty {
            request["keywords"] = keywords
        }
        if let id = id {
            request["id"] = id
        }
        if let agencies = agencies, !agencies.isEmpty {
            request["agencies"] = agencies
        }
        if let severity = severity {
            request["severity"] = severity.rawValue
        }
        if let riskCategory = riskCategory {
            request["riskCategory"] = riskCategory.rawValue
        }
        
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        
        if let dateFrom = dateFrom {
            request["date_from"] = dateFormatter.string(from: dateFrom)
        }
        if let dateTo = dateTo {
            request["date_to"] = dateFormatter.string(from: dateTo)
        }
        if let limit = limit {
            request["limit"] = min(max(1, limit), 50)
        }
        
        return request
    }
}

// MARK: - UI Helper Extensions

extension Severity {
    var displayName: String {
        switch self {
        case .low: return "Low"
        case .medium: return "Medium"
        case .high: return "High"
        case .critical: return "Critical"
        }
    }
    
    var color: String {
        switch self {
        case .critical: return "#8B0000"
        case .high: return "#FF0000"
        case .medium: return "#FFA500"
        case .low: return "#FFD700"
        }
    }
}

extension RecallItem {
    /// Check if recall is recent (within N days)
    func isRecent(days: Int = 30) -> Bool {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        
        guard let recallDate = dateFormatter.date(from: self.recallDate) else {
            return false
        }
        
        let calendar = Calendar.current
        guard let cutoffDate = calendar.date(byAdding: .day, value: -days, to: Date()) else {
            return false
        }
        
        return recallDate >= cutoffDate
    }
    
    /// Format recall date for display
    func formattedDate() -> String {
        let inputFormatter = DateFormatter()
        inputFormatter.dateFormat = "yyyy-MM-dd"
        
        guard let date = inputFormatter.date(from: self.recallDate) else {
            return self.recallDate
        }
        
        let outputFormatter = DateFormatter()
        outputFormatter.dateStyle = .medium
        outputFormatter.timeStyle = .none
        
        return outputFormatter.string(from: date)
    }
}
