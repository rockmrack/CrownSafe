# DataMatrix Barcode Support Setup

## Overview
DataMatrix barcode scanning is **disabled by default** due to complex system dependency requirements. This document explains how to enable it if needed.

## Current Status
- **Default**: Disabled (`ENABLE_DATAMATRIX=false`)
- **Reason**: Requires system libraries (`libdmtx0a/libdmtx0b`) that are difficult to install reliably in Docker
- **Impact**: Standard barcodes (UPC, EAN, QR codes) work perfectly without DataMatrix

## To Enable DataMatrix Support

### 1. Environment Variable
Set the environment variable:
```bash
ENABLE_DATAMATRIX=true
```

### 2. System Dependencies Required
The following system packages must be installed:
```bash
# Ubuntu/Debian
apt-get install libdmtx0a libdmtx-dev
# or
apt-get install libdmtx0b libdmtx-dev
```

### 3. Python Package Required
```bash
pip install pylibdmtx==0.1.10
```

## Docker Build Diagnostics

The Dockerfile includes comprehensive diagnostics to help troubleshoot DataMatrix installation:

1. **Package Search**: Shows available `libdmtx` packages
2. **Installation Attempts**: Tries multiple package variants
3. **Library Check**: Verifies libraries are loadable
4. **Python Import Test**: Confirms `pylibdmtx` works

## Alternative Solutions

If DataMatrix support is critical but installation fails:

1. **Use a different base image** (e.g., Ubuntu 20.04 vs 22.04)
2. **Build custom image** with DataMatrix pre-installed
3. **Use external service** for DataMatrix scanning
4. **Convert DataMatrix to QR codes** (if you control the generation)

## Testing DataMatrix

To test if DataMatrix is working:

```python
import os
os.environ['ENABLE_DATAMATRIX'] = 'true'

from core_infra.barcode_scanner import scanner
result = scanner.scan_image_data(datamatrix_image_bytes)
print(f"DataMatrix available: {scanner.DATAMATRIX_AVAILABLE}")
```

## Performance Impact

- **Disabled**: No performance impact
- **Enabled**: Minimal impact, only processes DataMatrix when detected

## Current Barcode Support (Without DataMatrix)

The system fully supports:
- ✅ **UPC/EAN**: Standard product barcodes
- ✅ **QR Codes**: 2D barcodes with high data capacity  
- ✅ **Code 128**: Variable-length alphanumeric
- ✅ **Code 39**: Alphanumeric barcodes
- ✅ **ITF**: Interleaved 2 of 5
- ✅ **PDF417**: 2D stacked barcode

DataMatrix is primarily used for:
- Industrial tracking
- Medical devices  
- Aerospace components
- Small item marking

For most baby product applications, QR codes provide equivalent functionality with better reliability.
