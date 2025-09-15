# Mobile App Integration Guide for Task 11

## Quick Start

### Base URL
```
Production: https://babyshield.cureviax.ai
```

---

## 1. OAuth Authentication

### Apple Sign-In (iOS)

```swift
import AuthenticationServices

class LoginViewController: UIViewController {
    
    @available(iOS 13.0, *)
    func signInWithApple() {
        let appleIDProvider = ASAuthorizationAppleIDProvider()
        let request = appleIDProvider.createRequest()
        request.requestedScopes = [.email]
        
        let authorizationController = ASAuthorizationController(authorizationRequests: [request])
        authorizationController.delegate = self
        authorizationController.presentationContextProvider = self
        authorizationController.performRequests()
    }
}

extension LoginViewController: ASAuthorizationControllerDelegate {
    func authorizationController(controller: ASAuthorizationController, 
                                  didCompleteWithAuthorization authorization: ASAuthorization) {
        if let appleIDCredential = authorization.credential as? ASAuthorizationAppleIDCredential {
            // Get the identity token
            guard let identityToken = appleIDCredential.identityToken,
                  let tokenString = String(data: identityToken, encoding: .utf8) else {
                return
            }
            
            // Send to your backend
            authenticateWithBackend(provider: "apple", idToken: tokenString)
        }
    }
    
    func authenticateWithBackend(provider: String, idToken: String) {
        let url = URL(string: "https://babyshield.cureviax.ai/api/v1/auth/oauth/login")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = [
            "provider": provider,
            "id_token": idToken,
            "device_id": UIDevice.current.identifierForVendor?.uuidString ?? "",
            "app_version": Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? ""
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let accessToken = json["access_token"] as? String,
                  let refreshToken = json["refresh_token"] as? String,
                  let userId = json["user_id"] as? String else {
                return
            }
            
            // Store tokens securely
            KeychainHelper.store(accessToken, key: "access_token")
            KeychainHelper.store(refreshToken, key: "refresh_token")
            UserDefaults.standard.set(userId, forKey: "user_id")
            
            DispatchQueue.main.async {
                // Navigate to main app
                self.navigateToMainApp()
            }
        }.resume()
    }
}
```

### Google Sign-In (Android)

```kotlin
// build.gradle
implementation 'com.google.android.gms:play-services-auth:20.7.0'

// LoginActivity.kt
class LoginActivity : AppCompatActivity() {
    
    private lateinit var googleSignInClient: GoogleSignInClient
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestIdToken(getString(R.string.default_web_client_id))
            .build()
            
        googleSignInClient = GoogleSignIn.getClient(this, gso)
    }
    
    private fun signInWithGoogle() {
        val signInIntent = googleSignInClient.signInIntent
        startActivityForResult(signInIntent, RC_SIGN_IN)
    }
    
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        
        if (requestCode == RC_SIGN_IN) {
            val task = GoogleSignIn.getSignedInAccountFromIntent(data)
            try {
                val account = task.getResult(ApiException::class.java)
                account?.idToken?.let { token ->
                    authenticateWithBackend("google", token)
                }
            } catch (e: ApiException) {
                Log.w(TAG, "Google sign in failed", e)
            }
        }
    }
    
    private fun authenticateWithBackend(provider: String, idToken: String) {
        val client = OkHttpClient()
        val json = JSONObject().apply {
            put("provider", provider)
            put("id_token", idToken)
            put("device_id", Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID))
            put("app_version", BuildConfig.VERSION_NAME)
        }
        
        val request = Request.Builder()
            .url("https://babyshield.cureviax.ai/api/v1/auth/oauth/login")
            .post(json.toString().toRequestBody("application/json".toMediaType()))
            .build()
            
        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                val responseBody = response.body?.string()
                val jsonResponse = JSONObject(responseBody ?: "{}")
                
                val accessToken = jsonResponse.getString("access_token")
                val refreshToken = jsonResponse.getString("refresh_token")
                val userId = jsonResponse.getString("user_id")
                
                // Store tokens securely
                SecurePreferences.storeAccessToken(accessToken)
                SecurePreferences.storeRefreshToken(refreshToken)
                getSharedPreferences("app_prefs", MODE_PRIVATE)
                    .edit()
                    .putString("user_id", userId)
                    .apply()
                    
                runOnUiThread {
                    startActivity(Intent(this@LoginActivity, MainActivity::class.java))
                    finish()
                }
            }
            
            override fun onFailure(call: Call, e: IOException) {
                Log.e(TAG, "Authentication failed", e)
            }
        })
    }
    
    companion object {
        private const val RC_SIGN_IN = 9001
        private const val TAG = "LoginActivity"
    }
}
```

---

## 2. Data Export & Deletion

### React Native Implementation

```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert } from 'react-native';

class PrivacyManager {
    
    async exportUserData() {
        const userId = await AsyncStorage.getItem('user_id');
        const accessToken = await AsyncStorage.getItem('access_token');
        
        try {
            const response = await fetch('https://babyshield.cureviax.ai/api/v1/user/data/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`,
                    'X-User-ID': userId
                },
                body: JSON.stringify({
                    user_id: userId,
                    format: 'json',
                    include_logs: false
                })
            });
            
            const data = await response.json();
            
            if (data.ok) {
                if (data.status === 'completed' && data.data) {
                    // Handle the exported data
                    this.displayExportedData(data.data);
                } else {
                    // Show status
                    Alert.alert('Export Started', `Request ID: ${data.request_id}`);
                    // Poll for status
                    this.pollExportStatus(data.request_id);
                }
            }
        } catch (error) {
            Alert.alert('Error', 'Failed to export data');
        }
    }
    
    async deleteAccount() {
        Alert.alert(
            'Delete Account',
            'This will permanently delete all your data. This action cannot be undone.\n\nAre you absolutely sure?',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Delete',
                    style: 'destructive',
                    onPress: () => this.confirmDeletion()
                }
            ]
        );
    }
    
    async confirmDeletion() {
        const userId = await AsyncStorage.getItem('user_id');
        const accessToken = await AsyncStorage.getItem('access_token');
        
        try {
            const response = await fetch('https://babyshield.cureviax.ai/api/v1/user/data/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`,
                    'X-User-ID': userId
                },
                body: JSON.stringify({
                    user_id: userId,
                    confirm: true,
                    reason: 'User requested account deletion'
                })
            });
            
            const data = await response.json();
            
            if (data.ok) {
                // Clear all local data
                await AsyncStorage.clear();
                
                // Navigate to login
                Alert.alert(
                    'Account Deleted',
                    'Your account has been permanently deleted.',
                    [{ text: 'OK', onPress: () => this.navigateToLogin() }]
                );
            }
        } catch (error) {
            Alert.alert('Error', 'Failed to delete account');
        }
    }
}
```

---

## 3. Crashlytics Toggle

### Flutter Implementation

```dart
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class CrashlyticsManager {
  static const String _crashlyticsKey = 'crashlytics_enabled';
  static const String _baseUrl = 'https://babyshield.cureviax.ai';
  
  // Check current status
  static Future<bool> isEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    // Default is OFF for privacy
    return prefs.getBool(_crashlyticsKey) ?? false;
  }
  
  // Toggle Crashlytics
  static Future<void> setCrashlyticsEnabled(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();
    final userId = prefs.getString('user_id') ?? 'anonymous';
    
    // Update backend
    final response = await http.post(
      Uri.parse('$_baseUrl/api/v1/settings/crashlytics'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'enabled': enabled,
        'user_id': userId,
        'device_id': await getDeviceId(),
        'app_version': await getAppVersion(),
      }),
    );
    
    if (response.statusCode == 200) {
      // Update local setting
      await prefs.setBool(_crashlyticsKey, enabled);
      
      // Enable/disable Crashlytics SDK
      await FirebaseCrashlytics.instance
          .setCrashlyticsCollectionEnabled(enabled);
      
      if (enabled) {
        // Set user identifier for crash reports (no PII)
        await FirebaseCrashlytics.instance.setUserIdentifier(userId);
      }
    } else {
      throw Exception('Failed to update Crashlytics setting');
    }
  }
  
  // Initialize on app start
  static Future<void> initialize() async {
    final enabled = await isEnabled();
    
    // Apply saved setting
    await FirebaseCrashlytics.instance
        .setCrashlyticsCollectionEnabled(enabled);
    
    if (!enabled) {
      print('Crashlytics is disabled by user preference');
    }
  }
}

// Settings UI
class SettingsScreen extends StatefulWidget {
  @override
  _SettingsScreenState createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _crashlyticsEnabled = false;
  
  @override
  void initState() {
    super.initState();
    _loadSettings();
  }
  
  Future<void> _loadSettings() async {
    final enabled = await CrashlyticsManager.isEnabled();
    setState(() {
      _crashlyticsEnabled = enabled;
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Settings')),
      body: ListView(
        children: [
          SwitchListTile(
            title: Text('Crash Reporting'),
            subtitle: Text('Help improve the app by sending crash reports'),
            value: _crashlyticsEnabled,
            onChanged: (bool value) async {
              if (value) {
                // Show privacy notice when enabling
                final confirm = await showDialog<bool>(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: Text('Enable Crash Reporting'),
                    content: Text(
                      'This will send anonymous crash reports to help improve the app. '
                      'No personal information is included.\n\n'
                      'You can disable this at any time.'
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(false),
                        child: Text('Cancel'),
                      ),
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(true),
                        child: Text('Enable'),
                      ),
                    ],
                  ),
                );
                
                if (confirm != true) return;
              }
              
              try {
                await CrashlyticsManager.setCrashlyticsEnabled(value);
                setState(() {
                  _crashlyticsEnabled = value;
                });
              } catch (e) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Failed to update setting')),
                );
              }
            },
          ),
          // Data management buttons
          ListTile(
            title: Text('Export My Data'),
            leading: Icon(Icons.download),
            onTap: () => _exportData(),
          ),
          ListTile(
            title: Text('Delete My Account'),
            leading: Icon(Icons.delete_forever, color: Colors.red),
            textColor: Colors.red,
            onTap: () => _deleteAccount(),
          ),
        ],
      ),
    );
  }
}
```

---

## 4. Offline & Retry Logic

```javascript
// NetworkManager.js
class NetworkManager {
    constructor() {
        this.retryPolicy = null;
        this.loadRetryPolicy();
    }
    
    async loadRetryPolicy() {
        try {
            const response = await fetch('https://babyshield.cureviax.ai/api/v1/settings/retry-policy');
            this.retryPolicy = await response.json();
        } catch (error) {
            // Use default policy
            this.retryPolicy = {
                retry_policy: {
                    max_retries: 3,
                    initial_delay_ms: 1000,
                    max_delay_ms: 30000,
                    backoff_multiplier: 2,
                    retry_on_status_codes: [408, 429, 500, 502, 503, 504]
                }
            };
        }
    }
    
    async fetchWithRetry(url, options = {}, retryCount = 0) {
        try {
            const response = await fetch(url, options);
            
            if (response.ok) {
                return response;
            }
            
            // Check if we should retry
            const shouldRetry = this.retryPolicy.retry_policy.retry_on_status_codes
                .includes(response.status);
                
            if (shouldRetry && retryCount < this.retryPolicy.retry_policy.max_retries) {
                const delay = Math.min(
                    this.retryPolicy.retry_policy.initial_delay_ms * 
                    Math.pow(this.retryPolicy.retry_policy.backoff_multiplier, retryCount),
                    this.retryPolicy.retry_policy.max_delay_ms
                );
                
                await new Promise(resolve => setTimeout(resolve, delay));
                return this.fetchWithRetry(url, options, retryCount + 1);
            }
            
            return response;
        } catch (error) {
            // Network error - retry if allowed
            if (retryCount < this.retryPolicy.retry_policy.max_retries) {
                const delay = this.retryPolicy.retry_policy.initial_delay_ms * 
                    Math.pow(this.retryPolicy.retry_policy.backoff_multiplier, retryCount);
                    
                await new Promise(resolve => setTimeout(resolve, delay));
                return this.fetchWithRetry(url, options, retryCount + 1);
            }
            
            throw error;
        }
    }
}
```

---

## API Response Format

All endpoints return consistent JSON responses:

### Success Response
```json
{
    "ok": true,
    "data": { ... },
    "trace_id": "trace_abc123"
}
```

### Error Response
```json
{
    "ok": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message"
    },
    "trace_id": "trace_xyz789"
}
```

---

## Important Notes

1. **Privacy First**: 
   - Crashlytics is OFF by default
   - No email storage for OAuth users
   - Only hashed provider IDs stored

2. **Token Management**:
   - Access tokens expire in 1 hour
   - Refresh tokens expire in 30 days
   - Implement automatic refresh

3. **Error Handling**:
   - Always show clear error messages
   - Implement retry logic for network failures
   - Queue actions when offline

4. **Security**:
   - Store tokens in secure storage (Keychain/Keystore)
   - Never log tokens or sensitive data
   - Use HTTPS for all requests

---

## Testing

Before app store submission:
1. Test OAuth with real Apple/Google accounts
2. Verify Crashlytics toggle works
3. Test data export returns actual data
4. Confirm deletion requires explicit confirmation
5. Test offline mode and retry logic
6. Verify no PII is stored or transmitted

---

## Support

For issues or questions:
- API Documentation: https://babyshield.cureviax.ai/docs
- Health Check: https://babyshield.cureviax.ai/api/v1/healthz
- Version Info: https://babyshield.cureviax.ai/api/v1/version
