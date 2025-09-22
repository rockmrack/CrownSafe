# Mobile App Integration Guide - Production Ready

## Quick Start

### Base URL
```
Production: https://babyshield.cureviax.ai
```

---

## Authentication Endpoints (Corrected)

Based on **live production testing** (256 endpoints confirmed):

### **Register**
- **Endpoint:** `POST /api/v1/auth/register`
- **Content-Type:** `application/json`
- **Body:** `{ "email", "password", "confirm_password" }`

### **Login**
- **Endpoint:** `POST /api/v1/auth/token` (**NOT** `/api/v1/auth/login`)
- **Content-Type:** `application/x-www-form-urlencoded` (**NOT** JSON)
- **Body:** `username=<email>&password=<password>`

### **Current User**
- **GET** `/api/v1/auth/me` → 200 if valid, 401 if token revoked
- **PUT** `/api/v1/auth/me` → Update current user (as defined in OpenAPI)

### **Account Deletion**
- **Endpoint:** `DELETE /api/v1/account`
- **Returns:** `204 No Content`
- **After deletion:** Subsequent calls with same token → `401 Unauthorized` ("Token revoked")

### **Legacy Endpoint (DO NOT USE)**
- **Endpoint:** `POST /api/v1/user/data/delete`
- **Returns:** **Non-2xx** (observed `400` when body missing)
- **Status:** **Deprecated** - Use `DELETE /api/v1/account` instead

---

## iOS Swift Implementation (Corrected)

```swift
import Foundation

class BabyShieldAPI {
    private let baseURL = "https://babyshield.cureviax.ai"
    
    // CORRECTED: Login uses form-urlencoded, not JSON
    func login(email: String, password: String, completion: @escaping (Result<LoginResponse, Error>) -> Void) {
        let url = URL(string: "\(baseURL)/api/v1/auth/token")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        
        // Form-encoded body
        let bodyString = "username=\(email.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")&password=\(password.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")"
        request.httpBody = bodyString.data(using: .utf8)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            // Handle response
            if let data = data {
                do {
                    let loginResponse = try JSONDecoder().decode(LoginResponse.self, from: data)
                    completion(.success(loginResponse))
                } catch {
                    completion(.failure(error))
                }
            }
        }.resume()
    }
    
    // Register uses JSON
    func register(email: String, password: String, confirmPassword: String, completion: @escaping (Result<RegisterResponse, Error>) -> Void) {
        let url = URL(string: "\(baseURL)/api/v1/auth/register")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = [
            "email": email,
            "password": password,
            "confirm_password": confirmPassword
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            // Handle response
        }.resume()
    }
    
    // CORRECTED: Account deletion returns 204, then token is revoked
    func deleteAccount(accessToken: String, completion: @escaping (Result<Void, Error>) -> Void) {
        let url = URL(string: "\(baseURL)/api/v1/account")!
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let httpResponse = response as? HTTPURLResponse {
                if httpResponse.statusCode == 204 {
                    // Success - account deleted
                    // NOTE: This token is now revoked
                    completion(.success(()))
                } else if httpResponse.statusCode == 401 {
                    // Re-authentication required or token already revoked
                    completion(.failure(APIError.reAuthRequired))
                }
            }
        }.resume()
    }
    
    // Test if token is still valid
    func getCurrentUser(accessToken: String, completion: @escaping (Result<User, Error>) -> Void) {
        let url = URL(string: "\(baseURL)/api/v1/auth/me")!
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let httpResponse = response as? HTTPURLResponse {
                if httpResponse.statusCode == 401 {
                    // Token revoked or expired
                    completion(.failure(APIError.tokenRevoked))
                    return
                }
            }
            // Handle success response
        }.resume()
    }
}

struct LoginResponse: Codable {
    let access_token: String
    let token_type: String
    let refresh_token: String
}

struct RegisterResponse: Codable {
    let ok: Bool
    let data: RegisterData
}

struct RegisterData: Codable {
    let user_id: String
    let access_token: String
    let refresh_token: String
}

enum APIError: Error {
    case reAuthRequired
    case tokenRevoked
}
```

---

## Android Kotlin Implementation (Corrected)

```kotlin
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import com.google.gson.Gson
import java.io.IOException

class BabyShieldAPI {
    private val baseUrl = "https://babyshield.cureviax.ai"
    private val client = OkHttpClient()
    private val gson = Gson()
    
    // CORRECTED: Login uses form-urlencoded
    fun login(email: String, password: String, callback: (Result<LoginResponse>) -> Unit) {
        val formBody = FormBody.Builder()
            .add("username", email)
            .add("password", password)
            .build()
        
        val request = Request.Builder()
            .url("$baseUrl/api/v1/auth/token")
            .post(formBody)
            .build()
        
        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                if (response.isSuccessful) {
                    val loginResponse = gson.fromJson(response.body?.string(), LoginResponse::class.java)
                    callback(Result.success(loginResponse))
                } else {
                    callback(Result.failure(Exception("Login failed: ${response.code}")))
                }
            }
            
            override fun onFailure(call: Call, e: IOException) {
                callback(Result.failure(e))
            }
        })
    }
    
    // Register uses JSON
    fun register(email: String, password: String, confirmPassword: String, callback: (Result<RegisterResponse>) -> Unit) {
        val registerRequest = mapOf(
            "email" to email,
            "password" to password,
            "confirm_password" to confirmPassword
        )
        
        val json = gson.toJson(registerRequest)
        val body = json.toRequestBody("application/json".toMediaType())
        
        val request = Request.Builder()
            .url("$baseUrl/api/v1/auth/register")
            .post(body)
            .build()
        
        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                if (response.isSuccessful) {
                    val registerResponse = gson.fromJson(response.body?.string(), RegisterResponse::class.java)
                    callback(Result.success(registerResponse))
                }
            }
            
            override fun onFailure(call: Call, e: IOException) {
                callback(Result.failure(e))
            }
        })
    }
    
    // CORRECTED: Account deletion returns 204, then token is revoked
    fun deleteAccount(accessToken: String, callback: (Result<Unit>) -> Unit) {
        val request = Request.Builder()
            .url("$baseUrl/api/v1/account")
            .delete()
            .addHeader("Authorization", "Bearer $accessToken")
            .build()
        
        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                when (response.code) {
                    204 -> {
                        // Success - account deleted
                        // NOTE: This token is now revoked
                        callback(Result.success(Unit))
                    }
                    401 -> {
                        // Re-authentication required or token already revoked
                        callback(Result.failure(Exception("Re-authentication required")))
                    }
                    429 -> {
                        callback(Result.failure(Exception("Too many requests")))
                    }
                    else -> {
                        callback(Result.failure(Exception("Deletion failed: ${response.code}")))
                    }
                }
            }
            
            override fun onFailure(call: Call, e: IOException) {
                callback(Result.failure(e))
            }
        })
    }
}

data class LoginResponse(
    val access_token: String,
    val token_type: String,
    val refresh_token: String
)

data class RegisterResponse(
    val ok: Boolean,
    val data: RegisterData
)

data class RegisterData(
    val user_id: String,
    val access_token: String,
    val refresh_token: String
)
```

---

## Legal & Privacy Pages (Corrected)

### **Account Deletion Page**
- **URL:** `https://babyshield.cureviax.ai/legal/account-deletion`
- **Returns:** `200 OK` with HTML content

### **Data Deletion Redirect**
- **URL:** `https://babyshield.cureviax.ai/legal/data-deletion`
- **Returns:** `301 Redirect` to `/legal/account-deletion`
- **Note:** Some stacks return `405` for `HEAD`; use `GET` when checking redirect

### **Privacy Policy**
- **URL:** `https://babyshield.cureviax.ai/legal/privacy`
- **Returns:** `200 OK` with HTML content

---

## Real Data Endpoints (Confirmed Live)

### **Risk Assessment Stats**
```
GET /api/v1/risk-assessment/stats → 200 OK
```

### **Supplemental Data Sources**
```
GET /api/v1/supplemental/data-sources → 200 OK
```

---

## Documentation Links (Corrected)

- **Swagger UI**: https://babyshield.cureviax.ai/docs
- **ReDoc**: https://babyshield.cureviax.ai/redoc
- **OpenAPI JSON**: https://babyshield.cureviax.ai/openapi.json

---

## Key Differences from Previous Docs

1. **Login endpoint** is `/auth/token` (not `/auth/login`)
2. **Login uses form-urlencoded** (not JSON)
3. **Account deletion returns 204** then token becomes invalid
4. **Legacy endpoint returns 400** (not 410) when body missing
5. **Legal redirect** returns 301 (confirmed behavior)
6. **Total endpoints: 256** (confirmed live)

---

## Testing Checklist

Before app store submission:
- [ ] Test login with form-urlencoded format
- [ ] Verify account deletion returns 204
- [ ] Confirm token becomes invalid after deletion
- [ ] Test legal page redirects work with GET requests
- [ ] Verify real data endpoints return 200
- [ ] Check all documentation links work

---

## Support

For issues or questions:
- API Documentation: https://babyshield.cureviax.ai/docs
- Health Check: https://babyshield.cureviax.ai/api/v1/healthz
- Total Live Endpoints: **256** (confirmed)
