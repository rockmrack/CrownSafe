# Task 12: Mobile Barcode Scanner Integration Guide

## Camera Permission Copy & Implementation

---

## 1. Camera Permission Text

### iOS (Info.plist)
```xml
<key>NSCameraUsageDescription</key>
<string>BabyShield needs camera access to scan product barcodes and check for safety recalls. No photos are stored.</string>
```

### Android (strings.xml)
```xml
<string name="camera_permission_rationale">BabyShield needs camera access to scan product barcodes and check for safety recalls. No photos are stored.</string>
<string name="camera_permission_denied">Camera permission is required to scan barcodes. Please enable it in Settings.</string>
```

### In-App Permission Dialog Copy

**Title:** "Enable Camera for Barcode Scanning"

**Body:** "To check if products have safety recalls, BabyShield needs to scan their barcodes. We only process barcode data—no photos are saved or transmitted."

**Buttons:**
- Primary: "Enable Camera"
- Secondary: "Not Now"

**Denied/Settings Redirect:**
"You can enable camera access anytime in Settings > BabyShield > Camera"

---

## 2. iOS Implementation (Swift)

### Setup

**Podfile:**
```ruby
pod 'AVFoundation'
pod 'BarcodeScanner', '~> 5.0'
# Or use native AVFoundation
```

### Native Implementation

```swift
import UIKit
import AVFoundation

class BarcodeScannerViewController: UIViewController {
    
    // MARK: - Properties
    private var captureSession: AVCaptureSession!
    private var previewLayer: AVCaptureVideoPreviewLayer!
    private var scanCache = BarcodeScanCache(maxSize: 50)
    private let hapticFeedback = UIImpactFeedbackGenerator(style: .light)
    
    // UI Elements
    private let scannerView = UIView()
    private let resultLabel = UILabel()
    private let instructionLabel = UILabel()
    private let torchButton = UIButton()
    
    // MARK: - Lifecycle
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        checkCameraPermission()
    }
    
    // MARK: - Camera Permission
    
    private func checkCameraPermission() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            setupCamera()
            
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                DispatchQueue.main.async {
                    if granted {
                        self?.setupCamera()
                    } else {
                        self?.showPermissionDenied()
                    }
                }
            }
            
        case .denied, .restricted:
            showPermissionDenied()
            
        @unknown default:
            break
        }
    }
    
    private func showPermissionDenied() {
        let alert = UIAlertController(
            title: "Camera Access Required",
            message: "BabyShield needs camera access to scan product barcodes. Please enable it in Settings.",
            preferredStyle: .alert
        )
        
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel))
        alert.addAction(UIAlertAction(title: "Settings", style: .default) { _ in
            if let settingsUrl = URL(string: UIApplication.openSettingsURLString) {
                UIApplication.shared.open(settingsUrl)
            }
        })
        
        present(alert, animated: true)
    }
    
    // MARK: - Camera Setup
    
    private func setupCamera() {
        captureSession = AVCaptureSession()
        
        guard let videoCaptureDevice = AVCaptureDevice.default(for: .video) else {
            showError("Camera not available")
            return
        }
        
        do {
            let videoInput = try AVCaptureDeviceInput(device: videoCaptureDevice)
            
            if captureSession.canAddInput(videoInput) {
                captureSession.addInput(videoInput)
            }
            
            let metadataOutput = AVCaptureMetadataOutput()
            
            if captureSession.canAddOutput(metadataOutput) {
                captureSession.addOutput(metadataOutput)
                
                metadataOutput.setMetadataObjectsDelegate(self, queue: DispatchQueue.main)
                
                // Support multiple barcode types
                metadataOutput.metadataObjectTypes = [
                    .ean8,
                    .ean13,
                    .upce,
                    .code128,
                    .code39,
                    .qr,
                    .dataMatrix
                ]
            }
            
            // Setup preview layer
            previewLayer = AVCaptureVideoPreviewLayer(session: captureSession)
            previewLayer.frame = scannerView.bounds
            previewLayer.videoGravity = .resizeAspectFill
            scannerView.layer.addSublayer(previewLayer)
            
            // Start capture session
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                self?.captureSession.startRunning()
            }
            
        } catch {
            showError("Failed to setup camera: \(error.localizedDescription)")
        }
    }
    
    // MARK: - UI Setup
    
    private func setupUI() {
        view.backgroundColor = .systemBackground
        
        // Scanner view
        scannerView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(scannerView)
        
        // Instruction label
        instructionLabel.text = "Point camera at product barcode"
        instructionLabel.textAlignment = .center
        instructionLabel.font = .systemFont(ofSize: 16, weight: .medium)
        instructionLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(instructionLabel)
        
        // Result label
        resultLabel.textAlignment = .center
        resultLabel.numberOfLines = 0
        resultLabel.font = .systemFont(ofSize: 14)
        resultLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(resultLabel)
        
        // Torch button
        torchButton.setImage(UIImage(systemName: "flashlight.off.fill"), for: .normal)
        torchButton.addTarget(self, action: #selector(toggleTorch), for: .touchUpInside)
        torchButton.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(torchButton)
        
        // Layout
        NSLayoutConstraint.activate([
            scannerView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            scannerView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            scannerView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            scannerView.heightAnchor.constraint(equalTo: view.heightAnchor, multiplier: 0.6),
            
            instructionLabel.topAnchor.constraint(equalTo: scannerView.bottomAnchor, constant: 20),
            instructionLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            instructionLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            
            resultLabel.topAnchor.constraint(equalTo: instructionLabel.bottomAnchor, constant: 20),
            resultLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            resultLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            
            torchButton.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 20),
            torchButton.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            torchButton.widthAnchor.constraint(equalToConstant: 44),
            torchButton.heightAnchor.constraint(equalToConstant: 44)
        ])
    }
    
    @objc private func toggleTorch() {
        guard let device = AVCaptureDevice.default(for: .video),
              device.hasTorch else { return }
        
        do {
            try device.lockForConfiguration()
            device.torchMode = device.torchMode == .on ? .off : .on
            device.unlockForConfiguration()
            
            let imageName = device.torchMode == .on ? "flashlight.on.fill" : "flashlight.off.fill"
            torchButton.setImage(UIImage(systemName: imageName), for: .normal)
        } catch {
            print("Failed to toggle torch: \(error)")
        }
    }
}

// MARK: - Barcode Detection

extension BarcodeScannerViewController: AVCaptureMetadataOutputObjectsDelegate {
    
    func metadataOutput(_ output: AVCaptureMetadataOutput, 
                        didOutput metadataObjects: [AVMetadataObject], 
                        from connection: AVCaptureConnection) {
        
        guard let metadataObject = metadataObjects.first,
              let readableObject = metadataObject as? AVMetadataMachineReadableCodeObject,
              let barcode = readableObject.stringValue else { return }
        
        // Haptic feedback
        hapticFeedback.prepare()
        hapticFeedback.impactOccurred()
        
        // Stop scanning temporarily
        captureSession.stopRunning()
        
        // Check cache first
        if let cachedResult = scanCache.get(barcode: barcode) {
            displayResult(cachedResult, fromCache: true)
        } else {
            // Make API call
            scanBarcode(barcode)
        }
    }
    
    private func scanBarcode(_ barcode: String) {
        // Show loading
        resultLabel.text = "Checking barcode..."
        
        let url = URL(string: "https://babyshield.cureviax.ai/api/v1/barcode/scan")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "barcode": barcode,
            "include_similar": true,
            "user_id": UserDefaults.standard.string(forKey: "user_id") ?? ""
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            guard let data = data,
                  let result = try? JSONDecoder().decode(BarcodeScanResponse.self, from: data) else {
                DispatchQueue.main.async {
                    self?.showError("Failed to check barcode")
                    self?.resumeScanning()
                }
                return
            }
            
            DispatchQueue.main.async {
                // Cache the result
                self?.scanCache.set(barcode: barcode, data: result)
                
                // Display result
                self?.displayResult(result, fromCache: false)
            }
        }.resume()
    }
    
    private func displayResult(_ result: BarcodeScanResponse, fromCache: Bool) {
        var message = ""
        
        if fromCache {
            message += "📦 Cached Result\n"
        }
        
        switch result.matchStatus {
        case "exact_match":
            message += "⚠️ RECALL FOUND!\n"
            message += "\(result.recalls.count) recall(s) for this product"
            
        case "similar_found":
            message += "ℹ️ No direct match—showing similar recalls\n"
            message += "\(result.recalls.count) similar product recall(s)"
            
        case "no_recalls":
            message += "✅ No recalls found\n"
            message += "This product appears to be safe"
            
        default:
            message += "No information available"
        }
        
        resultLabel.text = message
        
        // Show details or resume scanning after delay
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in
            self?.resumeScanning()
        }
    }
    
    private func resumeScanning() {
        resultLabel.text = ""
        captureSession.startRunning()
    }
    
    private func showError(_ message: String) {
        let alert = UIAlertController(title: "Error", message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default))
        present(alert, animated: true)
    }
}

// MARK: - Local Cache Implementation

class BarcodeScanCache {
    private var cache: [String: BarcodeScanResponse] = [:]
    private var cacheOrder: [String] = []
    private let maxSize: Int
    
    init(maxSize: Int = 50) {
        self.maxSize = maxSize
    }
    
    func get(barcode: String) -> BarcodeScanResponse? {
        guard let result = cache[barcode] else { return nil }
        
        // Move to front (LRU)
        if let index = cacheOrder.firstIndex(of: barcode) {
            cacheOrder.remove(at: index)
            cacheOrder.insert(barcode, at: 0)
        }
        
        return result
    }
    
    func set(barcode: String, data: BarcodeScanResponse) {
        // Add to cache
        cache[barcode] = data
        
        // Update order
        if let index = cacheOrder.firstIndex(of: barcode) {
            cacheOrder.remove(at: index)
        }
        cacheOrder.insert(barcode, at: 0)
        
        // Enforce max size
        if cacheOrder.count > maxSize {
            if let removed = cacheOrder.popLast() {
                cache.removeValue(forKey: removed)
            }
        }
    }
    
    func clear() {
        cache.removeAll()
        cacheOrder.removeAll()
    }
}

// MARK: - Response Model

struct BarcodeScanResponse: Codable {
    let ok: Bool
    let barcode: String
    let matchStatus: String
    let message: String?
    let recalls: [RecallMatch]
    let totalRecalls: Int
    let cached: Bool
    
    struct RecallMatch: Codable {
        let recallId: String
        let productName: String
        let brand: String?
        let hazard: String?
        let matchConfidence: Double
        let matchType: String
    }
}
```

---

## 3. Android Implementation (Kotlin)

### Setup

**build.gradle:**
```gradle
dependencies {
    implementation 'com.google.mlkit:barcode-scanning:17.2.0'
    implementation 'androidx.camera:camera-camera2:1.3.0'
    implementation 'androidx.camera:camera-lifecycle:1.3.0'
    implementation 'androidx.camera:camera-view:1.3.0'
}
```

### Implementation

```kotlin
class BarcodeScannerActivity : AppCompatActivity() {
    
    private lateinit var cameraProvider: ProcessCameraProvider
    private lateinit var camera: Camera
    private lateinit var preview: Preview
    private lateinit var imageAnalyzer: ImageAnalysis
    private val scanCache = BarcodeScanCache(50)
    
    // UI Elements
    private lateinit var previewView: PreviewView
    private lateinit var resultTextView: TextView
    private lateinit var instructionTextView: TextView
    private lateinit var torchButton: ImageButton
    
    companion object {
        private const val CAMERA_PERMISSION_REQUEST = 1001
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_barcode_scanner)
        
        setupUI()
        checkCameraPermission()
    }
    
    // Camera Permission
    private fun checkCameraPermission() {
        when {
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.CAMERA
            ) == PackageManager.PERMISSION_GRANTED -> {
                startCamera()
            }
            
            ActivityCompat.shouldShowRequestPermissionRationale(
                this,
                Manifest.permission.CAMERA
            ) -> {
                showPermissionRationale()
            }
            
            else -> {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.CAMERA),
                    CAMERA_PERMISSION_REQUEST
                )
            }
        }
    }
    
    private fun showPermissionRationale() {
        AlertDialog.Builder(this)
            .setTitle("Camera Permission Needed")
            .setMessage(getString(R.string.camera_permission_rationale))
            .setPositiveButton("Grant") { _, _ ->
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.CAMERA),
                    CAMERA_PERMISSION_REQUEST
                )
            }
            .setNegativeButton("Cancel") { _, _ ->
                finish()
            }
            .show()
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        
        if (requestCode == CAMERA_PERMISSION_REQUEST) {
            if (grantResults.isNotEmpty() && 
                grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startCamera()
            } else {
                showPermissionDenied()
            }
        }
    }
    
    private fun showPermissionDenied() {
        AlertDialog.Builder(this)
            .setTitle("Camera Permission Required")
            .setMessage(getString(R.string.camera_permission_denied))
            .setPositiveButton("Settings") { _, _ ->
                val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                intent.data = Uri.fromParts("package", packageName, null)
                startActivity(intent)
            }
            .setNegativeButton("Cancel") { _, _ ->
                finish()
            }
            .show()
    }
    
    // Camera Setup
    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        
        cameraProviderFuture.addListener({
            cameraProvider = cameraProviderFuture.get()
            bindCameraUseCases()
        }, ContextCompat.getMainExecutor(this))
    }
    
    private fun bindCameraUseCases() {
        // Preview use case
        preview = Preview.Builder().build()
        preview.setSurfaceProvider(previewView.surfaceProvider)
        
        // Image analysis use case for barcode scanning
        imageAnalyzer = ImageAnalysis.Builder()
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .build()
            
        val barcodeScanner = BarcodeScanning.getClient()
        
        imageAnalyzer.setAnalyzer(
            ContextCompat.getMainExecutor(this),
            BarcodeAnalyzer(barcodeScanner) { barcode ->
                handleBarcodeDetected(barcode)
            }
        )
        
        // Select back camera
        val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
        
        try {
            // Unbind all use cases before rebinding
            cameraProvider.unbindAll()
            
            // Bind use cases to camera
            camera = cameraProvider.bindToLifecycle(
                this,
                cameraSelector,
                preview,
                imageAnalyzer
            )
            
            // Setup torch button
            setupTorchButton()
            
        } catch (e: Exception) {
            Log.e("BarcodeScanner", "Use case binding failed", e)
            showError("Failed to start camera")
        }
    }
    
    // Barcode Analysis
    inner class BarcodeAnalyzer(
        private val scanner: BarcodeScanner,
        private val onBarcodeDetected: (String) -> Unit
    ) : ImageAnalysis.Analyzer {
        
        @androidx.camera.core.ExperimentalGetImage
        override fun analyze(imageProxy: ImageProxy) {
            val mediaImage = imageProxy.image
            if (mediaImage != null) {
                val image = InputImage.fromMediaImage(
                    mediaImage,
                    imageProxy.imageInfo.rotationDegrees
                )
                
                scanner.process(image)
                    .addOnSuccessListener { barcodes ->
                        for (barcode in barcodes) {
                            barcode.rawValue?.let { value ->
                                onBarcodeDetected(value)
                            }
                        }
                    }
                    .addOnCompleteListener {
                        imageProxy.close()
                    }
            } else {
                imageProxy.close()
            }
        }
    }
    
    // Handle Detected Barcode
    private fun handleBarcodeDetected(barcode: String) {
        // Vibrate for feedback
        val vibrator = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            @Suppress("DEPRECATION")
            vibrator.vibrate(100)
        }
        
        // Stop scanning temporarily
        imageAnalyzer.clearAnalyzer()
        
        // Check cache first
        val cachedResult = scanCache.get(barcode)
        if (cachedResult != null) {
            displayResult(cachedResult, fromCache = true)
        } else {
            // Make API call
            scanBarcode(barcode)
        }
    }
    
    private fun scanBarcode(barcode: String) {
        runOnUiThread {
            resultTextView.text = "Checking barcode..."
        }
        
        val client = OkHttpClient()
        val requestBody = JSONObject().apply {
            put("barcode", barcode)
            put("include_similar", true)
            put("user_id", getSharedPreferences("app_prefs", MODE_PRIVATE)
                .getString("user_id", ""))
        }
        
        val request = Request.Builder()
            .url("https://babyshield.cureviax.ai/api/v1/barcode/scan")
            .post(requestBody.toString().toRequestBody("application/json".toMediaType()))
            .build()
        
        client.newCall(request).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                val responseBody = response.body?.string()
                val result = Gson().fromJson(responseBody, BarcodeScanResponse::class.java)
                
                runOnUiThread {
                    // Cache the result
                    scanCache.set(barcode, result)
                    
                    // Display result
                    displayResult(result, fromCache = false)
                }
            }
            
            override fun onFailure(call: Call, e: IOException) {
                runOnUiThread {
                    showError("Failed to check barcode")
                    resumeScanning()
                }
            }
        })
    }
    
    private fun displayResult(result: BarcodeScanResponse, fromCache: Boolean) {
        val message = buildString {
            if (fromCache) {
                appendLine("📦 Cached Result")
            }
            
            when (result.matchStatus) {
                "exact_match" -> {
                    appendLine("⚠️ RECALL FOUND!")
                    append("${result.recalls.size} recall(s) for this product")
                }
                
                "similar_found" -> {
                    appendLine("ℹ️ No direct match—showing similar recalls")
                    append("${result.recalls.size} similar product recall(s)")
                }
                
                "no_recalls" -> {
                    appendLine("✅ No recalls found")
                    append("This product appears to be safe")
                }
                
                else -> append("No information available")
            }
        }
        
        resultTextView.text = message
        
        // Resume scanning after delay
        Handler(Looper.getMainLooper()).postDelayed({
            resumeScanning()
        }, 3000)
    }
    
    private fun resumeScanning() {
        resultTextView.text = ""
        bindCameraUseCases()
    }
    
    // UI Setup
    private fun setupUI() {
        previewView = findViewById(R.id.previewView)
        resultTextView = findViewById(R.id.resultTextView)
        instructionTextView = findViewById(R.id.instructionTextView)
        torchButton = findViewById(R.id.torchButton)
        
        instructionTextView.text = "Point camera at product barcode"
    }
    
    private fun setupTorchButton() {
        torchButton.setOnClickListener {
            if (camera.cameraInfo.hasFlashUnit()) {
                val torchState = camera.cameraInfo.torchState.value ?: TorchState.OFF
                camera.cameraControl.enableTorch(torchState == TorchState.OFF)
                
                val icon = if (torchState == TorchState.OFF) {
                    R.drawable.ic_flashlight_on
                } else {
                    R.drawable.ic_flashlight_off
                }
                torchButton.setImageResource(icon)
            }
        }
    }
    
    private fun showError(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }
}

// Cache Implementation
class BarcodeScanCache(private val maxSize: Int = 50) {
    private val cache = LinkedHashMap<String, BarcodeScanResponse>(maxSize + 1, 0.75f, true)
    
    fun get(barcode: String): BarcodeScanResponse? {
        return cache[barcode]
    }
    
    fun set(barcode: String, data: BarcodeScanResponse) {
        cache[barcode] = data
        
        // Remove oldest if exceeds max size
        if (cache.size > maxSize) {
            val iterator = cache.entries.iterator()
            iterator.next()
            iterator.remove()
        }
    }
    
    fun clear() {
        cache.clear()
    }
}

// Data Models
data class BarcodeScanResponse(
    val ok: Boolean,
    val barcode: String,
    val matchStatus: String,
    val message: String?,
    val recalls: List<RecallMatch>,
    val totalRecalls: Int,
    val cached: Boolean
)

data class RecallMatch(
    val recallId: String,
    val productName: String,
    val brand: String?,
    val hazard: String?,
    val matchConfidence: Double,
    val matchType: String
)
```

---

## 4. React Native Implementation

```javascript
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Alert,
  Vibration,
  TouchableOpacity,
  ActivityIndicator
} from 'react-native';
import { RNCamera } from 'react-native-camera';
import BarcodeMask from 'react-native-barcode-mask';
import AsyncStorage from '@react-native-async-storage/async-storage';

const CACHE_KEY = 'barcode_cache';
const MAX_CACHE_SIZE = 50;

export default function BarcodeScanner({ navigation }) {
  const [scanning, setScanning] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [torchOn, setTorchOn] = useState(false);
  const [cache, setCache] = useState({});

  useEffect(() => {
    loadCache();
    return () => saveCache();
  }, []);

  // Cache Management
  const loadCache = async () => {
    try {
      const cached = await AsyncStorage.getItem(CACHE_KEY);
      if (cached) {
        setCache(JSON.parse(cached));
      }
    } catch (error) {
      console.error('Failed to load cache:', error);
    }
  };

  const saveCache = async () => {
    try {
      // Keep only last 50 entries
      const entries = Object.entries(cache)
        .sort((a, b) => b[1].timestamp - a[1].timestamp)
        .slice(0, MAX_CACHE_SIZE);
      
      await AsyncStorage.setItem(CACHE_KEY, JSON.stringify(Object.fromEntries(entries)));
    } catch (error) {
      console.error('Failed to save cache:', error);
    }
  };

  const getCached = (barcode) => {
    const cached = cache[barcode];
    if (cached) {
      // Check if cache is still valid (24 hours)
      const age = Date.now() - cached.timestamp;
      if (age < 24 * 60 * 60 * 1000) {
        return cached.data;
      }
    }
    return null;
  };

  const setCached = (barcode, data) => {
    setCache(prev => ({
      ...prev,
      [barcode]: {
        data,
        timestamp: Date.now()
      }
    }));
  };

  // Barcode Detection
  const onBarcodeRead = async (scanResult) => {
    if (!scanning) return;
    
    const { data: barcode, type } = scanResult;
    
    // Vibrate for feedback
    Vibration.vibrate(100);
    
    // Stop scanning
    setScanning(false);
    setLoading(true);
    
    // Check cache first
    const cached = getCached(barcode);
    if (cached) {
      displayResult({ ...cached, cached: true });
      return;
    }
    
    // Make API call
    try {
      const response = await fetch('https://babyshield.cureviax.ai/api/v1/barcode/scan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': await AsyncStorage.getItem('user_id') || ''
        },
        body: JSON.stringify({
          barcode,
          barcode_type: type,
          include_similar: true
        })
      });
      
      const data = await response.json();
      
      if (data.ok) {
        // Cache the result
        setCached(barcode, data);
        
        // Display result
        displayResult(data);
      } else {
        showError('Failed to check barcode');
      }
    } catch (error) {
      showError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const displayResult = (data) => {
    setResult(data);
    
    let title = '';
    let message = '';
    let type = 'info';
    
    if (data.cached) {
      message += '📦 Cached result\n\n';
    }
    
    switch (data.match_status) {
      case 'exact_match':
        title = '⚠️ Recall Found!';
        message += `${data.total_recalls} recall(s) found for this product.`;
        type = 'warning';
        break;
        
      case 'similar_found':
        title = 'ℹ️ Similar Products';
        message += 'No direct match—showing similar recalls\n';
        message += `${data.total_recalls} similar product recall(s) found.`;
        break;
        
      case 'no_recalls':
        title = '✅ No Recalls';
        message += 'This product appears to be safe.';
        type = 'success';
        break;
        
      default:
        title = 'No Information';
        message += 'No information available for this barcode.';
    }
    
    Alert.alert(
      title,
      message,
      [
        {
          text: 'View Details',
          onPress: () => {
            navigation.navigate('RecallDetails', { data });
          },
          style: data.total_recalls > 0 ? 'default' : 'cancel'
        },
        {
          text: 'Scan Another',
          onPress: resumeScanning,
          style: 'cancel'
        }
      ]
    );
  };

  const resumeScanning = () => {
    setResult(null);
    setScanning(true);
  };

  const showError = (message) => {
    Alert.alert('Error', message, [
      { text: 'OK', onPress: resumeScanning }
    ]);
  };

  return (
    <View style={styles.container}>
      <RNCamera
        style={styles.camera}
        type={RNCamera.Constants.Type.back}
        flashMode={torchOn ? RNCamera.Constants.FlashMode.torch : RNCamera.Constants.FlashMode.off}
        onBarCodeRead={onBarcodeRead}
        captureAudio={false}
      >
        <BarcodeMask
          width={280}
          height={180}
          showAnimatedLine={scanning}
          outerMaskOpacity={0.6}
        />
        
        <View style={styles.overlay}>
          <Text style={styles.instruction}>
            Point camera at product barcode
          </Text>
          
          {loading && (
            <ActivityIndicator size="large" color="#fff" style={styles.loader} />
          )}
        </View>
        
        <TouchableOpacity
          style={styles.torchButton}
          onPress={() => setTorchOn(!torchOn)}
        >
          <Text style={styles.torchText}>
            {torchOn ? '🔦' : '📵'}
          </Text>
        </TouchableOpacity>
      </RNCamera>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'black'
  },
  camera: {
    flex: 1
  },
  overlay: {
    position: 'absolute',
    top: 100,
    left: 0,
    right: 0,
    alignItems: 'center'
  },
  instruction: {
    color: 'white',
    fontSize: 16,
    backgroundColor: 'rgba(0,0,0,0.6)',
    padding: 10,
    borderRadius: 5
  },
  loader: {
    marginTop: 20
  },
  torchButton: {
    position: 'absolute',
    top: 50,
    right: 20,
    padding: 10,
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderRadius: 25
  },
  torchText: {
    fontSize: 24
  }
});
```

---

## 5. Testing & Acceptance

### Test Barcodes

| Barcode | Expected Behavior | Test Case |
|---------|-------------------|-----------|
| `070470003795` | Exact match found | Gerber product recall |
| `037000123456` | Similar products shown | P&G brand fallback |
| `999999999999` | No recalls found | Unknown product |
| `12345678` | Valid UPC-E processed | Short barcode |
| `5901234123457` | Valid EAN-13 processed | International product |

### Acceptance Criteria

- [ ] Camera permission requested with proper copy
- [ ] Permission denial handled gracefully
- [ ] Settings redirect available
- [ ] Barcode detection works for UPC/EAN
- [ ] Exact matches show immediately
- [ ] Fallback shows "No direct match—showing similar recalls"
- [ ] Last 50 scans cached locally
- [ ] Cache persists between sessions
- [ ] Offline scans show cached results
- [ ] Torch/flashlight toggle works
- [ ] Haptic/vibration feedback on scan
- [ ] Loading state during API call
- [ ] Error states handled gracefully
- [ ] Resume scanning after result

---

## 6. Performance & UX Guidelines

### Scanning Performance
- Camera preview: 30+ FPS
- Barcode detection: < 500ms
- API response: < 2 seconds
- Cache lookup: < 10ms

### User Experience
- Clear scanning area indicator
- Animated scanning line
- Immediate haptic feedback
- Clear result messaging
- Easy rescan option

### Error Handling
- Network errors: Show cached or retry
- Invalid barcode: Continue scanning
- API errors: Graceful fallback
- Permission denied: Clear instructions

---

## Support

For additional barcode types or custom implementations, contact support@babyshield.app
