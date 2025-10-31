# AWS to Azure Migration - Crown Safe

**Started:** October 31, 2025  
**Status:** 🚧 IN PROGRESS (78% Complete - 7/9 tasks done)  
**Objective:** Migrate entire codebase from AWS (S3, boto3) to Azure (Blob Storage, azure-storage-blob)

---

## 📊 Migration Progress

### ✅ Completed (7/9 tasks)
1. **Azure Storage Abstraction Layer** - Created `core_infra/azure_storage.py` with download_blob() method
2. **Requirements Update** - Replaced `boto3==1.34.2` with `azure-storage-blob==12.19.0` and `azure-identity==1.15.0`
3. **Share Results Endpoints** - Migrated `api/share_results_endpoints.py` to Azure Blob Storage
4. **Risk Report Generator** - Migrated `core_infra/risk_report_generator.py` to Azure Blob Storage
5. **Crown Safe Visual Endpoints** - Migrated `api/crown_safe_visual_endpoints.py` to Azure Blob Storage
6. **Visual Search Agent** - Migrated `agents/visual/visual_search_agent/agent_logic.py` to Azure Blob Storage
7. **Environment Configuration** - Updated `.env.example` and `api/main_crownsafe.py` CORS configuration

### ⏸️ Pending (2/9 tasks)
8. **Documentation Updates** - Update README, copilot-instructions, deployment guides
9. **Database Migration** - Create Alembic migration for s3_url → blob_url column rename

---

## 🔄 Migration Mappings

### AWS → Azure Service Equivalents

| AWS Service      | Azure Service                     | Python SDK                  |
| ---------------- | --------------------------------- | --------------------------- |
| AWS S3           | Azure Blob Storage                | `azure-storage-blob`        |
| boto3            | azure-identity                    | `azure-identity`            |
| S3 Bucket        | Blob Container                    | Same concept                |
| S3 Key           | Blob Name                         | Same concept                |
| S3 Presigned URL | SAS (Shared Access Signature) URL | Different authentication    |
| AWS CloudWatch   | Azure Monitor                     | Different SDK               |
| AWS RDS          | Azure Database for PostgreSQL     | Different connection string |

### Code Pattern Replacements

#### Before (AWS S3)
```python
import boto3

s3_client = boto3.client("s3", region_name="us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "crownsafe-images")

# Upload file
s3_client.put_object(
    Bucket=S3_BUCKET,
    Key=key,
    Body=file_data,
    ContentType="application/pdf"
)

# Check if exists
s3_client.head_object(Bucket=S3_BUCKET, Key=key)

# Generate presigned URL
url = s3_client.generate_presigned_url(
    'get_object',
    Params={'Bucket': S3_BUCKET, 'Key': key},
    ExpiresIn=3600
)
```

#### After (Azure Blob Storage)
```python
from core_infra.azure_storage import get_azure_storage_client

storage_client = get_azure_storage_client(container_name="crownsafe-images")

# Upload file
blob_url = storage_client.upload_file(
    file_data=file_data,
    blob_name=key,
    content_type="application/pdf"
)

# Check if exists
exists = storage_client.blob_exists(blob_name=key)
# OR
properties = storage_client.head_object(blob_name=key)

# Generate SAS URL
sas_url = storage_client.generate_sas_url(
    blob_name=key,
    expiry_hours=1
)
```

---

## 📝 Files Modified

### ✅ Completed Files

#### 1. **core_infra/azure_storage.py** (NEW FILE - 388 lines)
**Created:** Azure Blob Storage abstraction layer

**Key Features:**
- `AzureBlobStorageClient` class with full Azure Blob Storage support
- `upload_file()` - Upload bytes to blob
- `upload_file_from_path()` - Upload from file path
- `generate_sas_url()` - Create temporary access URLs
- `blob_exists()` - Check blob existence
- `head_object()` - Get blob properties (S3-compatible method)
- `delete_blob()` - Delete blobs
- `list_blobs()` - List blobs with prefix filter
- `get_blob_url()` - Get public blob URL
- `is_azure_blob_url()` - Static URL validator

**Configuration:**
```python
# Via connection string (preferred)
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...

# Via account name + key
AZURE_STORAGE_ACCOUNT_NAME=crownsafestorage
AZURE_STORAGE_ACCOUNT_KEY=your-access-key

# Via managed identity (production)
AZURE_STORAGE_ACCOUNT_NAME=crownsafestorage
# Uses DefaultAzureCredential automatically
```

#### 2. **config/requirements/requirements.txt**
**Changed:**
```diff
# Cloud Services
- boto3==1.34.2  # AWS SDK
+ azure-storage-blob==12.19.0  # Azure Blob Storage (replaces AWS S3)
+ azure-identity==1.15.0  # Azure authentication
google-cloud-vision==3.5.0  # Google Cloud Vision
firebase-admin==6.3.0  # Firebase for push notifications
```

#### 3. **api/share_results_endpoints.py** (1,105 lines)
**Changes:**
- ✅ Removed `import boto3`
- ✅ Added `from core_infra.azure_storage import get_azure_storage_client`
- ✅ Replaced `s3_client = boto3.client("s3")` with `storage_client = get_azure_storage_client()`
- ✅ Renamed `_guess_s3_key()` → `_guess_blob_key()`
- ✅ Renamed `create_share_token_for_s3()` → `create_share_token_for_azure_blob()`
- ✅ Replaced `s3_client.head_object(Bucket=..., Key=...)` → `storage_client.head_object(blob_name=...)`
- ✅ Updated content snapshots: `s3_key` → `blob_key`
- ✅ Updated report attributes: `report.s3_url` → `report.blob_url`

---

### 🚧 In Progress Files

#### 4. **core_infra/risk_report_generator.py**
**Status:** Needs migration - S3 upload functionality

**Current Issues:**
```python
import boto3  # ❌ Need to remove

def __init__(self, s3_client=None):
    self.s3_client = s3_client or boto3.client("s3")  # ❌ Replace with Azure
    self.bucket_name = os.getenv("S3_BUCKET_NAME", "babyshield-reports")  # ❌ Change to Azure

def _upload_to_s3(self, ...):  # ❌ Rename to _upload_to_azure_blob
    s3_enabled = os.getenv("S3_ENABLED", "false").lower() == "true"  # ❌ Change to AZURE_BLOB_ENABLED
    self.s3_client.head_bucket(Bucket=self.bucket_name)  # ❌ Replace with Azure check
    self.s3_client.put_object(...)  # ❌ Replace with storage_client.upload_file()
    url = self.s3_client.generate_presigned_url(...)  # ❌ Replace with generate_sas_url()
```

**Required Changes:**
```python
from core_infra.azure_storage import get_azure_storage_client

def __init__(self, storage_client=None):
    self.storage_client = storage_client or get_azure_storage_client()
    self.container_name = os.getenv("AZURE_STORAGE_CONTAINER", "crownsafe-reports")

def _upload_to_azure_blob(self, key: str, pdf_data: bytes, html_data: str, json_data: str):
    """Upload report to Azure Blob Storage and return SAS URL"""
    
    azure_blob_enabled = os.getenv("AZURE_BLOB_ENABLED", "false").lower() == "true"
    if not azure_blob_enabled:
        return local_path
    
    try:
        # Upload PDF
        self.storage_client.upload_file(
            file_data=pdf_data,
            blob_name=f"{key}.pdf",
            content_type="application/pdf"
        )
        
        # Upload HTML
        self.storage_client.upload_file(
            file_data=html_data.encode('utf-8'),
            blob_name=f"{key}.html",
            content_type="text/html"
        )
        
        # Upload JSON
        self.storage_client.upload_file(
            file_data=json_data.encode('utf-8'),
            blob_name=f"{key}.json",
            content_type="application/json"
        )
        
        # Generate SAS URL (1 hour expiry)
        url = self.storage_client.generate_sas_url(
            blob_name=f"{key}.pdf",
            expiry_hours=1
        )
        
        return url
    except Exception as e:
        logger.error(f"Azure Blob upload failed: {e}")
        return local_path
```

---

### ⏸️ Pending Files

#### 5. **api/crown_safe_visual_endpoints.py**
**Location:** Lines 30, 46-49

**Current Code:**
```python
import boto3

# AWS Configuration (if using cloud storage)
AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")
S3_BUCKET_REGION = os.getenv("S3_BUCKET_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_UPLOAD_BUCKET", "crownsafe-images")
```

**Required Changes:**
```python
from core_infra.azure_storage import get_azure_storage_client

# Azure Configuration
AZURE_REGION = os.getenv("AZURE_REGION", "eastus2")
STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "crownsafe-images")
storage_client = get_azure_storage_client(container_name=STORAGE_CONTAINER)
```

#### 6. **agents/visual/visual_search_agent/agent_logic.py**
**Location:** Lines 14-38

**Current Code:**
```python
def _is_s3_url(url: str) -> bool:
    """Check if URL is an S3 URL"""
    u = urlparse(url)
    return u.scheme == "s3" or ("amazonaws.com" in (u.netloc or ""))

def _get_image_bytes(image_url: str) -> bytes:
    # For presigned S3 HTTPS or any external CDN → use HTTP GET
    if _is_s3_url(image_url) and image_url.startswith("s3://"):
        # s3://bucket/key → boto3
        import boto3
        
        parts = image_url[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        
        s3 = boto3.client("s3", region_name="us-east-1")
        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()
```

**Required Changes:**
```python
from core_infra.azure_storage import AzureBlobStorageClient

def _is_azure_blob_url(url: str) -> bool:
    """Check if URL is an Azure Blob Storage URL"""
    return AzureBlobStorageClient.is_azure_blob_url(url)

def _get_image_bytes(image_url: str) -> bytes:
    # For Azure Blob Storage URLs
    if _is_azure_blob_url(image_url):
        from core_infra.azure_storage import get_azure_storage_client
        
        # Parse blob URL to extract container and blob name
        parsed = urlparse(image_url)
        path_parts = parsed.path.lstrip('/').split('/', 1)
        container = path_parts[0]
        blob_name = path_parts[1] if len(path_parts) > 1 else ""
        
        storage_client = get_azure_storage_client(container_name=container)
        blob_client = storage_client._get_blob_client(blob_name)
        return blob_client.download_blob().readall()
    
    # For HTTP/HTTPS URLs (including SAS URLs), use requests
    response = requests.get(image_url)
    response.raise_for_status()
    return response.content
```

#### 7. **api/main_crownsafe.py**
**Location:** Line 453

**Current Code:**
```python
allow_origins=[
    "https://cureviax.ai",
    "https://babyshield.cureviax.ai",
    "https://crownsafe.cureviax.ai",
    "*.amazonaws.com",  # ❌ AWS CloudFront
    "http://localhost:3000",
    "http://localhost:8000",
],
```

**Required Changes:**
```python
allow_origins=[
    "https://cureviax.ai",
    "https://babyshield.cureviax.ai",
    "https://crownsafe.cureviax.ai",
    "*.blob.core.windows.net",  # ✅ Azure Blob Storage
    "*.azurewebsites.net",  # ✅ Azure Web Apps
    "http://localhost:3000",
    "http://localhost:8000",
],
```

---

## 🔐 Environment Variables

### Old (AWS)
```bash
# AWS S3
S3_ENABLED=true
S3_BUCKET=crownsafe-images
S3_BUCKET_NAME=babyshield-reports
S3_BUCKET_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=eu-north-1
```

### New (Azure)
```bash
# Azure Blob Storage
AZURE_BLOB_ENABLED=true
AZURE_STORAGE_CONTAINER=crownsafe-images

# Option 1: Connection String (Recommended for Development)
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=crownsafestorage;AccountKey=xxxxx;EndpointSuffix=core.windows.net

# Option 2: Account Name + Key (Alternative)
AZURE_STORAGE_ACCOUNT_NAME=crownsafestorage
AZURE_STORAGE_ACCOUNT_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Option 3: Managed Identity (Production - No credentials needed)
AZURE_STORAGE_ACCOUNT_NAME=crownsafestorage
# Uses DefaultAzureCredential with managed identity

# Azure Region
AZURE_REGION=eastus2
```

---

## 🗄️ Database Schema Changes

### SafetyReport Model
**Required Changes:**
```python
class SafetyReport(Base):
    __tablename__ = "safety_reports"
    
    # Old
    s3_url = Column(String, nullable=True)  # ❌ AWS S3 URL
    
    # New
    blob_url = Column(String, nullable=True)  # ✅ Azure Blob Storage SAS URL
```

**Migration Script Needed:**
```sql
-- Rename column
ALTER TABLE safety_reports RENAME COLUMN s3_url TO blob_url;

-- Update documentation comments
COMMENT ON COLUMN safety_reports.blob_url IS 'Azure Blob Storage SAS URL for the report';
```

---

## 📚 Documentation Updates Needed

### Files to Update:
1. **README.md** - Lines 29, 168, 180-183, 217
   - Replace "AWS Account (for ECR, S3)" → "Azure Account (for Blob Storage)"
   - Replace "AWS Secrets Manager" → "Azure Key Vault"
   - Replace "AWS ECR" → "Azure Container Registry (ACR)"
   - Replace "AWS ECS/EKS" → "Azure Container Instances/AKS"
   - Replace "AWS RDS PostgreSQL" → "Azure Database for PostgreSQL"
   - Replace "CloudWatch" → "Azure Monitor"

2. **.github/copilot-instructions.md** - Lines 13, 289, 497-498
   - Replace "AWS (boto3)" → "Azure (azure-storage-blob)"
   - Replace "AWS CloudWatch" → "Azure Monitor"
   - Remove AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
   - Add AZURE_STORAGE_CONNECTION_STRING

3. **.cursorrules** - Line 68
   - Replace "`Dockerfile.final` (AWS ECS)" → "`Dockerfile.final` (Azure Container Instances)"

4. **CROWN_SAFE_MVP_80_PERCENT_COMPLETE.md** - Line 302
   - Update deployment guide to use Azure instead of AWS

5. **.github/workflows/security-scan.yml** - Line 363
   - Replace Terrascan AWS scanning with Azure scanning
   - `terrascan scan -t aws` → `terrascan scan -t azure`

---

## 🧪 Testing Checklist

### Unit Tests Needed:
- [ ] Test `AzureBlobStorageClient.upload_file()`
- [ ] Test `AzureBlobStorageClient.generate_sas_url()`
- [ ] Test `AzureBlobStorageClient.blob_exists()`
- [ ] Test `AzureBlobStorageClient.head_object()`
- [ ] Test `AzureBlobStorageClient.delete_blob()`
- [ ] Test `AzureBlobStorageClient.list_blobs()`

### Integration Tests Needed:
- [ ] Test report generation with Azure Blob Storage upload
- [ ] Test share link generation with Azure SAS URLs
- [ ] Test visual search with Azure Blob Storage URLs
- [ ] Test crown safe visual endpoints with Azure storage
- [ ] Test error handling (missing credentials, invalid container)
- [ ] Test SAS URL expiration and regeneration

### Manual Tests Needed:
- [ ] Verify reports upload to Azure Blob Storage successfully
- [ ] Verify SAS URLs are accessible and expire correctly
- [ ] Verify share links work with Azure Blob Storage
- [ ] Verify image uploads for visual search
- [ ] Verify CORS configuration allows Azure domains
- [ ] Test managed identity authentication in Azure production environment

---

## 🚀 Deployment Steps

### Pre-Deployment:
1. Create Azure Storage Account (`crownsafestorage`)
2. Create blob container (`crownsafe-images`)
3. Configure CORS rules on Azure Blob Storage
4. Generate access keys or configure managed identity
5. Update environment variables in Azure App Service

### Database Migration:
```bash
# Create Alembic migration
alembic revision -m "Rename s3_url to blob_url in safety_reports"

# Apply migration to production
alembic upgrade head
```

### Code Deployment:
1. Install new Azure dependencies: `pip install -r config/requirements/requirements.txt`
2. Complete remaining file migrations (risk_report_generator.py, visual endpoints, visual agent)
3. Update environment variables
4. Run tests
5. Deploy to Azure App Service
6. Verify Azure Blob Storage connectivity
7. Monitor logs for any S3-related errors

### Post-Deployment:
1. Migrate existing S3 files to Azure Blob Storage (if any)
2. Update DNS/CDN to point to Azure Blob Storage URLs
3. Decommission AWS S3 buckets (after validation period)
4. Remove AWS credentials from environment

---

## ⚠️ Known Issues & Gotchas

### 1. **SAS URL Expiration**
Azure SAS URLs expire after a set time (default 24 hours). Unlike AWS S3 presigned URLs, SAS URLs cannot be regenerated without storage account access key.

**Solution:** Store blob keys in database and regenerate SAS URLs on-demand.

### 2. **CORS Configuration**
Azure Blob Storage CORS must be configured at the storage account level, not per-container.

**Azure Portal Steps:**
1. Go to Storage Account → Settings → Resource sharing (CORS)
2. Add Blob service CORS rule:
   - Allowed origins: `*` or specific domains
   - Allowed methods: GET, HEAD, PUT, POST
   - Allowed headers: `*`
   - Exposed headers: `*`
   - Max age: 3600

### 3. **Authentication Methods**
Azure supports multiple authentication methods:
- **Connection String** (easiest for development)
- **Access Key** (similar to AWS)
- **Managed Identity** (recommended for production, no credentials)
- **SAS Token** (for temporary access)

**Recommendation:** Use Managed Identity in Azure App Service production.

### 4. **Blob Naming Conventions**
Azure Blob Storage is case-sensitive and doesn't support certain characters in blob names (unlike S3):
- No backslashes (`\`)
- No trailing dots
- Max 1,024 characters

**Solution:** Sanitize blob names before upload.

### 5. **Public Access Levels**
Azure Blob Storage has different public access levels:
- **Private** (default) - Requires SAS token
- **Blob** - Anonymous read access to blobs only
- **Container** - Anonymous read access to container and blobs

**Recommendation:** Keep containers private and use SAS URLs for controlled access.

---

## 📊 Cost Comparison

### AWS S3 (Previous)
- Storage: ~$0.023/GB/month (Standard)
- GET requests: $0.0004/1,000 requests
- PUT requests: $0.005/1,000 requests
- Data transfer out: $0.09/GB (first 10 TB)

### Azure Blob Storage (New)
- Storage: ~$0.0208/GB/month (Hot tier)
- Operations: $0.0043/10,000 (Read), $0.043/10,000 (Write)
- Data transfer out: $0.087/GB (first 10 TB)

**Estimated Savings:** ~10% reduction in storage costs, similar operations costs.

---

## ✅ Next Steps (Priority Order)

1. **IMMEDIATE:**
   - [ ] Complete migration of `core_infra/risk_report_generator.py`
   - [ ] Test Azure Blob Storage client with real storage account

2. **HIGH PRIORITY:**
   - [ ] Migrate `api/crown_safe_visual_endpoints.py`
   - [ ] Migrate `agents/visual/visual_search_agent/agent_logic.py`
   - [ ] Update environment configuration files

3. **MEDIUM PRIORITY:**
   - [ ] Create database migration for `s3_url` → `blob_url`
   - [ ] Update documentation (README, copilot-instructions)
   - [ ] Configure CORS on Azure Blob Storage

4. **LOW PRIORITY:**
   - [ ] Write comprehensive tests
   - [ ] Update CI/CD workflows
   - [ ] Migrate existing S3 data to Azure (if applicable)

---

## 🔗 Useful Azure Resources

- [Azure Blob Storage Documentation](https://docs.microsoft.com/en-us/azure/storage/blobs/)
- [Python SDK Quickstart](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python)
- [Generate SAS Tokens](https://docs.microsoft.com/en-us/azure/storage/common/storage-sas-overview)
- [CORS Configuration](https://docs.microsoft.com/en-us/rest/api/storageservices/cross-origin-resource-sharing--cors--support-for-the-azure-storage-services)
- [Azure Storage Pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/)

---

**Last Updated:** October 31, 2025  
**Next Review:** After completing risk_report_generator.py migration
