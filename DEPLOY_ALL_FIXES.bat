@echo off
echo 🚀 Deploying all BabyShield fixes to GitHub...

REM Add all changes
git add .

REM Commit with comprehensive message
git commit -m "🔧 Complete system fixes and improvements

✅ DataMatrix barcode scanning fixes:
- Added pylibdmtx dependencies to Dockerfile and requirements
- Enhanced logging for DataMatrix initialization visibility
- Graceful fallback if dependencies unavailable

✅ Visual recognition fixes:
- Fixed missing 'import os' in advanced_features_endpoints.py
- Added graceful OpenAI API key handling in visual_search_agent
- Improved error responses (proper HTTP 500 instead of masked 200)
- Updated startup script to avoid mock API keys

✅ New features:
- Added barcode smoke test to CI pipeline (.github/workflows/ci.yml)
- Created clean lookup endpoints (api/routers/lookup.py)
- Added comprehensive regression checklist (REGRESSION_CHECKLIST.md)

✅ Enhanced logging and debugging:
- Forced console output for DataMatrix status
- Added explicit scanner initialization logging
- Improved error visibility throughout system

Fixes resolve: DataMatrix warnings, import errors, OpenAI crashes, error masking
New endpoints: GET /api/v1/lookup/barcode, automated CI testing
System status: Production ready with clear enhancement path"

REM Push to current branch
git push

echo ✅ All fixes deployed to GitHub!
pause
