"""
Root Main Entry Point for Docker Container
Issue #32 - Phase 2 Implementation
"""

import sys
import os
from pathlib import Path

# Ensure both root and api directories are in Python path
current_dir = Path(__file__).parent
api_dir = current_dir / "api"
sys.path.insert(0, str(current_dir))  # Add root directory first
sys.path.insert(0, str(api_dir))  # Add api directory (takes precedence)

# Import the FastAPI app from api directory
from main_babyshield import app

# Export the app for uvicorn
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
