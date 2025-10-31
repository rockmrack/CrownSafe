#!/usr/bin/env python3
"""
BabyShield Configuration Management Utility

This script helps manage configuration files, validate settings,
and generate secure secrets for production deployment.

Usage:
    python scripts/config_manager.py validate [environment]
    python scripts/config_manager.py generate-secrets
    python scripts/config_manager.py create-env [environment]
    python scripts/config_manager.py check-requirements
"""

import argparse
import os
import secrets
import string
import sys
from pathlib import Path
from typing import Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from config.settings.development import DevelopmentConfig  # noqa: F401
    from config.settings.production import ProductionConfig  # noqa: F401

    from config.settings import BaseConfig, get_config  # noqa: F401
except ImportError as e:
    print(f"❌ Error importing configuration: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


class ConfigManager:
    """Configuration management utility"""

    def __init__(self):
        self.project_root = project_root
        self.config_dir = self.project_root / "config"

    def generate_secret_key(self, length: int = 64) -> str:
        """Generate a secure secret key"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def generate_secrets(self) -> Dict[str, str]:
        """Generate secure secrets for production"""
        return {
            "SECRET_KEY": self.generate_secret_key(64),
            "POSTGRES_PASSWORD": self.generate_secret_key(32),
            "REDIS_PASSWORD": self.generate_secret_key(24),
        }

    def validate_config(self, environment: str = "development") -> bool:
        """Validate configuration for given environment"""
        print(f"🔍 Validating {environment} configuration...")

        try:
            config = get_config(environment)
            print("? Configuration loaded successfully")

            # Basic validation
            if not config.SECRET_KEY or len(config.SECRET_KEY) < 32:
                print("??  WARNING: SECRET_KEY is too short or missing")
                return False

            if environment == "production":
                if config.SECRET_KEY == "dev-secret-key-not-for-production":
                    print("❌ ERROR: Using development secret key in production!")
                    return False

                if config.DEBUG:
                    print("??  WARNING: DEBUG is enabled in production")

                if not config.DATABASE_URL.startswith(("postgresql://", "mysql://")):
                    print("??  WARNING: Not using production database")

            print("📋 Configuration summary:")
            print(f"   Environment: {environment}")
            print(f"   Debug: {config.DEBUG}")
            print(f"   Database: {config.DATABASE_URL[:20]}...")
            print(f"   Upload dir: {config.UPLOAD_DIR}")
            print(f"   Log level: {config.LOG_LEVEL}")

            return True

        except Exception as e:
            print(f"? Configuration validation failed: {e}")
            return False

    def create_env_file(self, environment: str) -> bool:
        """Create environment file from template"""
        allowed_envs = {"development", "staging", "production"}
        if environment not in allowed_envs:
            raise ValueError(f"Unsupported environment '{environment}'. Expected one of: {sorted(allowed_envs)}")

        template_file = self.project_root / f".env.{environment}.example"
        env_file = self.project_root / f".env.{environment}"

        if not template_file.exists():
            print(f"? Template file {template_file} not found")
            return False

        if env_file.exists():
            response = input(f"??  {env_file} already exists. Overwrite? (y/N): ")
            if response.lower() != "y":
                print("❌ Cancelled")
                return False

        # Copy template and replace placeholders
        content = template_file.read_text()

        if environment == "production":
            secrets_dict = self.generate_secrets()
            for key, value in secrets_dict.items():
                content = content.replace(f"your-{key.lower().replace('_', '-')}", value)

            print("🔐 Generated secure secrets for production:")
            for key in secrets_dict:
                print(f"   {key}: ********")

        env_file.write_text(content)
        print(f"✅ Created {env_file}")
        return True

    def check_requirements(self) -> bool:
        """Check if all required packages are available"""
        print("🔍 Checking configuration requirements...")

        # Package mapping: import_name -> package_name
        packages_to_check = {
            "pydantic": "pydantic",
            "yaml": "pyyaml",
            "decouple": "python-decouple",
            "dotenv": "python-dotenv",
        }

        missing = []
        for import_name, package_name in packages_to_check.items():
            try:
                __import__(import_name)
                print(f"✅ {package_name}")
            except ImportError:
                print(f"❌ {package_name}")
                missing.append(package_name)

        if missing:
            print("\n?? Install missing packages:")
            print(f"pip install {' '.join(missing)}")
            return False

        print("✅ All configuration requirements satisfied")
        return True

    def show_structure(self):
        """Show configuration directory structure"""
        print("📁 Configuration structure:")
        for root, dirs, files in os.walk(self.config_dir):
            level = root.replace(str(self.config_dir), "").count(os.sep)
            indent = " " * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = " " * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")


def main():
    parser = argparse.ArgumentParser(description="BabyShield Configuration Manager")
    parser.add_argument(
        "command",
        choices=[
            "validate",
            "generate-secrets",
            "create-env",
            "check-requirements",
            "show-structure",
        ],
    )
    parser.add_argument(
        "environment",
        nargs="?",
        default="development",
        choices=["development", "staging", "production"],
    )

    args = parser.parse_args()

    manager = ConfigManager()

    if args.command == "validate":
        success = manager.validate_config(args.environment)
        sys.exit(0 if success else 1)

    elif args.command == "generate-secrets":
        secrets_dict = manager.generate_secrets()
        print("🔐 Generated secure secrets:")
        for key, value in secrets_dict.items():
            print(f"{key}={value}")

    elif args.command == "create-env":
        success = manager.create_env_file(args.environment)
        sys.exit(0 if success else 1)

    elif args.command == "check-requirements":
        success = manager.check_requirements()
        sys.exit(0 if success else 1)

    elif args.command == "show-structure":
        manager.show_structure()


if __name__ == "__main__":
    main()
