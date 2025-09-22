# 🧪 BabyShield Visual Recognition Testing Guide

## Quick Start Commands

### 1. Basic Test (Production)
```powershell
.\TEST_VISUAL_RECOGNITION_SYSTEM.ps1 -BaseUrl "https://babyshield.cureviax.ai"
```

### 2. Test with API Key
```powershell
.\TEST_VISUAL_RECOGNITION_SYSTEM.ps1 -BaseUrl "https://babyshield.cureviax.ai" -ApiKey "your-api-key"
```

### 3. Test with Custom Image
```powershell
.\TEST_VISUAL_RECOGNITION_SYSTEM.ps1 -BaseUrl "https://babyshield.cureviax.ai" -TestImageUrl "https://your-test-image.jpg"
```

### 4. Test Local Development
```powershell
.\TEST_VISUAL_RECOGNITION_SYSTEM.ps1 -BaseUrl "http://localhost:8001"
```

---

## What Each Test Verifies

### 🏥 System Health Tests
- ✅ `/healthz` - Basic health check
- ✅ `/readyz` - Database connectivity
- ✅ `/docs` - API documentation availability

### 🔍 Simple Visual Search Tests  
- ✅ **GPT-4 Vision Integration** - Real AI product identification
- ✅ **Database Recall Checking** - Actual safety database queries
- ✅ **Error Handling** - Proper validation and error responses
- ✅ **Invalid URL Handling** - Graceful failure for bad images

### 🎯 Advanced Visual Recognition Tests
- ✅ **File Upload Processing** - S3 integration and image handling
- ✅ **Product Identification** - Complete pipeline from upload to analysis
- ✅ **Recall Status Checking** - Real database integration
- ✅ **Confidence Scoring** - AI confidence assessment

### 🔧 Defect Detection Tests
- ✅ **OpenCV Integration** - Computer vision defect detection (tested in Advanced Recognition)
- ✅ **Crack Detection** - Linear defect identification
- ✅ **Missing Parts Detection** - Component analysis
- ✅ **Color Anomaly Detection** - Discoloration/damage detection
- ✅ **Real-time Processing** - Integrated with image upload pipeline

### 💾 Database Integration Tests
- ✅ **Recall Database Access** - Query recall records
- ✅ **Search Functionality** - Advanced search capabilities
- ✅ **SQL Injection Protection** - Security validation

### 🤖 GPT-4 Vision Integration Tests
- ✅ **OpenAI API Connection** - Real AI service integration
- ✅ **Product Analysis** - Actual vs mock data verification
- ✅ **Confidence Scoring** - AI certainty assessment

### 🛡️ Error Handling & Resilience Tests
- ✅ **Invalid Endpoints** - 404 handling
- ✅ **Malformed JSON** - Input validation
- ✅ **Large Images** - Size limit handling

### ⚡ Performance Tests
- ✅ **Visual Search Response Time** - < 30 seconds
- ✅ **Health Check Speed** - < 2 seconds

---

## Expected Results

### ✅ **EXCELLENT (95%+ pass rate)**
```
📊 OVERALL RESULTS:
   Total Tests Run: 20
   Passed: 19
   Failed: 1
   Success Rate: 95.0%
   
🎯 SYSTEM STATUS ASSESSMENT:
   🟢 EXCELLENT - System is production-ready
```

### 🟡 **GOOD (85-94% pass rate)**
```
📊 OVERALL RESULTS:
   Total Tests Run: 20
   Passed: 17
   Failed: 3
   Success Rate: 85.0%
   
🎯 SYSTEM STATUS ASSESSMENT:
   🟡 GOOD - Minor issues, mostly production-ready
```

### 🔴 **NEEDS ATTENTION (<85% pass rate)**
```
📊 OVERALL RESULTS:
   Total Tests Run: 20
   Passed: 15
   Failed: 5
   Success Rate: 75.0%
   
🎯 SYSTEM STATUS ASSESSMENT:
   🟠 FAIR - Some issues need attention
```

---

## Sample Successful Test Output

```powershell
================================================================================
 2. SIMPLE VISUAL SEARCH ENDPOINT TESTS
================================================================================

🔍 Testing visual search with image URL...
✅ PASS: Visual Search with Image URL
   └─ Confidence: 0.87
   📊 Product Identified: Baby Bottle BPA-Free
   📊 Brand: Dr. Brown's
   📊 Confidence Level: high
   📊 Safety Status: no_recalls_found
   📊 Recall Check: Has Recalls = False

🔍 Testing visual search error handling...
✅ PASS: Visual Search Error Handling
   └─ Proper validation error returned

================================================================================
 4. DEFECT DETECTION SYSTEM TESTS
================================================================================

🔍 Testing defect detection system...
✅ PASS: Defect Detection System Active
   └─ OpenCV defect detection operational
✅ PASS: Defect Detection Results
   └─ Processed successfully, found 2 defects
   🔍 Defect Type: crack
   🔍 Severity: medium
   🔍 Confidence: 0.73
   🔍 Description: Linear crack detected (45x3 pixels)
```

---

## Troubleshooting

### Common Issues & Solutions

**❌ "Health Check Failed"**
```powershell
# Check if service is running
curl https://babyshield.cureviax.ai/healthz
```

**❌ "GPT-4 Vision API Integration Failed"**  
- Verify OPENAI_API_KEY is set in AWS environment
- Check CloudWatch logs for API errors

**❌ "Database Connection Failed"**
- Verify RDS instance is running
- Check security group settings
- Validate DATABASE_URL environment variable

**❌ "S3 Upload Failed"**
- Verify S3 bucket exists and is accessible
- Check IAM permissions for S3 access
- Validate AWS_REGION environment variable

**❌ "Defect Detection Failed"**
- OpenCV libraries may not be installed
- Check container image includes cv2 and numpy
- Review application logs for import errors

---

## Manual Verification Commands

### Test Individual Endpoints

```powershell
# Health Check
Invoke-RestMethod -Uri "https://babyshield.cureviax.ai/healthz"

# Simple Visual Search
$body = @{ image_url = "https://example.com/baby-bottle.jpg" } | ConvertTo-Json
Invoke-RestMethod -Uri "https://babyshield.cureviax.ai/api/v1/visual/search" -Method POST -Body $body -ContentType "application/json"

# Database Query
Invoke-RestMethod -Uri "https://babyshield.cureviax.ai/api/v1/recalls?limit=5"
```

---

## Log Analysis

### Check AWS CloudWatch Logs
```bash
# View recent application logs
aws logs tail /aws/ecs/babyshield-backend --follow

# Search for visual recognition errors
aws logs filter-log-events --log-group-name /aws/ecs/babyshield-backend --filter-pattern "visual.*error"

# Check GPT-4 Vision API calls
aws logs filter-log-events --log-group-name /aws/ecs/babyshield-backend --filter-pattern "OpenAI"
```

---

## Success Criteria

For production deployment, aim for:

- ✅ **95%+ test pass rate**
- ✅ **Visual search response time < 15 seconds**
- ✅ **Health check response time < 1 second** 
- ✅ **Real GPT-4 Vision integration working**
- ✅ **OpenCV defect detection operational**
- ✅ **Database queries returning real data**
- ✅ **S3 image upload/processing working**
- ✅ **Error handling graceful and informative**

Run the full test suite after every deployment to ensure all visual recognition components are functioning correctly.
