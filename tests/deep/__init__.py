"""
Deep test package initialization
Configures environment for comprehensive testing
"""

import os

# Enable chat feature for all deep tests
os.environ["BS_FEATURE_CHAT_ENABLED"] = "true"
os.environ["BS_FEATURE_CHAT_ROLLOUT_PCT"] = "1.0"
