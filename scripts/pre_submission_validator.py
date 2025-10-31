#!/usr/bin/env python3
"""BabyShield Pre-Submission Validator
Comprehensive validation before app store submission
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


class SubmissionValidator:
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.errors = []
        self.warnings = []
        self.successes = []
        self.checks_passed = 0
        self.checks_failed = 0

    def log_success(self, message: str):
        """Log a success message"""
        self.successes.append(message)
        self.checks_passed += 1
        print(f"  ✅ {message}")

    def log_error(self, message: str):
        """Log an error message"""
        self.errors.append(message)
        self.checks_failed += 1
        print(f"  ❌ {message}")

    def log_warning(self, message: str):
        """Log a warning message"""
        self.warnings.append(message)
        print(f"  ⚠️  {message}")

    def validate_json_file(self, path: Path, required_fields: list[str] = None) -> bool:
        """Validate a JSON file"""
        if not path.exists():
            self.log_error(f"Missing file: {path}")
            return False

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if required_fields:
                for field in required_fields:
                    if field not in data:
                        self.log_error(f"Missing field '{field}' in {path.name}")
                        return False

            self.log_success(f"Valid JSON: {path.name}")
            return True
        except json.JSONDecodeError as e:
            self.log_error(f"Invalid JSON in {path.name}: {e}")
            return False
        except Exception as e:
            self.log_error(f"Error reading {path.name}: {e}")
            return False

    def validate_text_file(self, path: Path, max_length: int = None, required_content: list[str] = None) -> bool:
        """Validate a text file"""
        if not path.exists():
            self.log_error(f"Missing file: {path}")
            return False

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            if max_length and len(content) > max_length:
                self.log_error(f"{path.name} exceeds {max_length} characters (has {len(content)})")
                return False

            if required_content:
                for req in required_content:
                    if req.lower() not in content.lower():
                        self.log_warning(f"{path.name} missing required content: '{req}'")

            self.log_success(f"Valid text file: {path.name}")
            return True
        except Exception as e:
            self.log_error(f"Error reading {path.name}: {e}")
            return False

    def validate_url(self, url: str, name: str) -> bool:
        """Validate that a URL is accessible"""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BabyShield/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    self.log_success(f"{name} accessible: {url}")
                    return True
                else:
                    self.log_warning(f"{name} returned status {response.status}: {url}")
                    return False
        except urllib.error.URLError as e:
            self.log_error(f"{name} not accessible: {url} - {e}")
            return False
        except Exception as e:
            self.log_warning(f"Could not verify {name}: {url} - {e}")
            return False

    def check_metadata_files(self):
        """Check all metadata files"""
        print("\n📋 Checking Metadata Files...")

        # Apple metadata
        apple_meta = self.base_path / "docs/store/apple/metadata.json"
        self.validate_json_file(
            apple_meta,
            [
                "appName",
                "bundleId",
                "primaryCategory",
                "sku",
                "privacyPolicyUrl",
                "reviewInformation",
            ],
        )

        # Google listing
        google_meta = self.base_path / "docs/store/google/listing.json"
        self.validate_json_file(
            google_meta,
            [
                "packageName",
                "title",
                "shortDescription",
                "privacyPolicyUrl",
                "contactEmail",
            ],
        )

        # Privacy labels
        apple_privacy = self.base_path / "docs/app_review/privacy_labels_apple.json"
        self.validate_json_file(apple_privacy)

        google_privacy = self.base_path / "docs/app_review/google_data_safety.json"
        self.validate_json_file(google_privacy)

    def check_descriptions(self):
        """Check description files"""
        print("\n📝 Checking Descriptions...")

        # Short tagline
        tagline = self.base_path / "docs/store/common/descriptions/short_tagline.txt"
        self.validate_text_file(tagline, max_length=80)

        # Long description
        long_desc = self.base_path / "docs/store/common/descriptions/long_description_en.txt"
        self.validate_text_file(
            long_desc,
            max_length=4000,
            required_content=["not medical advice", "privacy", "FDA", "CPSC"],
        )

    def check_assets(self):
        """Check asset files"""
        print("\n🎨 Checking Assets...")

        assets_path = self.base_path / "assets/store"

        # Check iOS assets
        ios_icon = assets_path / "icons/ios/AppIcon1024.png"
        if ios_icon.exists():
            self.log_success("iOS app icon present")
        else:
            self.log_error("iOS app icon missing: AppIcon1024.png")

        # Check iOS screenshots
        ios_screenshots = list((assets_path / "screenshots/ios").glob("*.png"))
        iphone67_count = len([f for f in ios_screenshots if "iphone67" in f.name])
        iphone65_count = len([f for f in ios_screenshots if "iphone65" in f.name])

        if iphone67_count >= 3:
            self.log_success(f'iPhone 6.7" screenshots: {iphone67_count} (minimum 3)')
        else:
            self.log_error(f'iPhone 6.7" screenshots: {iphone67_count} (need minimum 3)')

        if iphone65_count >= 3:
            self.log_success(f'iPhone 6.5" screenshots: {iphone65_count} (minimum 3)')
        else:
            self.log_error(f'iPhone 6.5" screenshots: {iphone65_count} (need minimum 3)')

        # Check Android assets
        android_icon = assets_path / "icons/android/Icon512.png"
        if android_icon.exists():
            self.log_success("Android app icon present")
        else:
            self.log_error("Android app icon missing: Icon512.png")

        feature_graphic = assets_path / "graphics/play-feature-1024x500.png"
        if feature_graphic.exists():
            self.log_success("Android feature graphic present")
        else:
            self.log_error("Android feature graphic missing")

        # Check Android screenshots
        android_screenshots = list((assets_path / "screenshots/android").glob("*.png"))
        phone_count = len([f for f in android_screenshots if "phone" in f.name])

        if phone_count >= 2:
            self.log_success(f"Android phone screenshots: {phone_count} (minimum 2)")
        else:
            self.log_error(f"Android phone screenshots: {phone_count} (need minimum 2)")

    def check_urls(self):
        """Check all URLs are accessible"""
        print("\n🌐 Checking URLs...")

        urls_to_check = [
            ("Privacy Policy", "https://babyshield.cureviax.ai/legal/privacy"),
            ("Terms of Service", "https://babyshield.cureviax.ai/legal/terms"),
            ("Data Deletion", "https://babyshield.cureviax.ai/legal/data-deletion"),
            ("Support Page", "https://babyshield.cureviax.ai/support"),
            ("Marketing Page", "https://babyshield.cureviax.ai"),
        ]

        for name, url in urls_to_check:
            self.validate_url(url, name)

    def check_api_endpoints(self):
        """Check API endpoints"""
        print("\n🔌 Checking API Endpoints...")

        base_url = "https://babyshield.cureviax.ai/api/v1"

        endpoints = [
            ("Health Check", f"{base_url}/healthz"),
            ("Version", f"{base_url}/version"),
            ("Privacy Summary", f"{base_url}/user/privacy/summary"),
        ]

        for name, url in endpoints:
            self.validate_url(url, name)

    def check_compliance(self):
        """Check compliance requirements"""
        print("\n⚖️ Checking Compliance...")

        # Check for required disclaimers
        long_desc_path = self.base_path / "docs/store/common/descriptions/long_description_en.txt"
        if long_desc_path.exists():
            with open(long_desc_path, "r", encoding="utf-8") as f:
                content = f.read().lower()

            if "not medical advice" in content:
                self.log_success("Medical disclaimer present")
            else:
                self.log_error("Medical disclaimer missing")

            if "privacy" in content and ("gdpr" in content or "ccpa" in content or "privacy" in content):
                self.log_success("Privacy information present")
            else:
                self.log_warning("Privacy compliance info should be mentioned")

        # Check age rating configuration
        apple_meta_path = self.base_path / "docs/store/apple/metadata.json"
        if apple_meta_path.exists():
            with open(apple_meta_path, "r", encoding="utf-8") as f:
                apple_data = json.load(f)

            if apple_data.get("ageRating", {}).get("ageRatingOverride") == "FOUR_PLUS":
                self.log_success("Age rating set to 4+")
            else:
                self.log_warning("Age rating should be 4+")

    def check_review_notes(self):
        """Check review notes completeness"""
        print("\n📄 Checking Review Notes...")

        # Apple review notes
        apple_notes = self.base_path / "docs/store/apple/review_notes.md"
        self.validate_text_file(
            apple_notes,
            required_content=[
                "Sign in with Apple",
                "Sign in with Google",
                "test",
                "pacifier",
                "not medical advice",
            ],
        )

        # Google review notes
        google_notes = self.base_path / "docs/store/google/review_notes.md"
        self.validate_text_file(google_notes, required_content=["OAuth", "test", "privacy"])

    def check_bundle_identifiers(self):
        """Check bundle identifiers consistency"""
        print("\n🔤 Checking Bundle Identifiers...")

        bundle_id = "ai.cureviax.babyshield"

        # Check in Apple metadata
        apple_meta_path = self.base_path / "docs/store/apple/metadata.json"
        if apple_meta_path.exists():
            with open(apple_meta_path, "r", encoding="utf-8") as f:
                apple_data = json.load(f)

            if apple_data.get("bundleId") == bundle_id:
                self.log_success(f"Apple bundle ID correct: {bundle_id}")
            else:
                self.log_error(f"Apple bundle ID mismatch: {apple_data.get('bundleId')} != {bundle_id}")

        # Check in Google metadata
        google_meta_path = self.base_path / "docs/store/google/listing.json"
        if google_meta_path.exists():
            with open(google_meta_path, "r", encoding="utf-8") as f:
                google_data = json.load(f)

            if google_data.get("packageName") == bundle_id:
                self.log_success(f"Google package name correct: {bundle_id}")
            else:
                self.log_error(f"Google package name mismatch: {google_data.get('packageName')} != {bundle_id}")

    def generate_submission_report(self):
        """Generate a submission readiness report"""
        report_path = self.base_path / "SUBMISSION_READINESS_REPORT.md"

        report = f"""# 📊 BabyShield Submission Readiness Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary

- **Checks Passed:** {self.checks_passed}
- **Checks Failed:** {self.checks_failed}
- **Warnings:** {len(self.warnings)}

## Status: {"🚀 READY FOR SUBMISSION" if self.checks_failed == 0 else "⚠️ NOT READY - ISSUES FOUND"}

"""

        if self.errors:
            report += "## ❌ Errors (Must Fix)\n\n"
            for error in self.errors:
                report += f"- {error}\n"
            report += "\n"

        if self.warnings:
            report += "## ⚠️ Warnings (Should Review)\n\n"
            for warning in self.warnings:
                report += f"- {warning}\n"
            report += "\n"

        if self.successes:
            report += "## ✅ Passed Checks\n\n"
            for success in self.successes:
                report += f"- {success}\n"
            report += "\n"

        report += """## Next Steps

"""

        if self.checks_failed == 0:
            report += """### You're ready to submit! 🎉

1. **Final Review:**
   - Review all metadata one more time
   - Ensure all assets are production quality
   - Test the app thoroughly

2. **Apple App Store:**
   - Archive app in Xcode
   - Upload via App Store Connect
   - Submit for review

3. **Google Play Store:**
   - Build AAB bundle
   - Upload to Play Console
   - Submit for review

4. **Monitor:**
   - Check review status daily
   - Respond to feedback quickly
   - Be ready to make adjustments
"""
        else:
            report += """### Fix these issues before submission:

1. **Address all errors** listed above
2. **Review warnings** and fix if possible
3. **Run validation again** after fixes
4. **Ensure all checks pass** before submission

Re-run this validator:
```bash
python scripts/pre_submission_validator.py
```
"""

        report += """
## Checklist References

- [Submission Checklist](docs/store/SUBMISSION_CHECKLIST.md)
- [Required Assets](docs/store/REQUIRED_ASSETS.md)
- [Screenshot Guide](docs/store/SCREENSHOT_CAPTURE_GUIDE.md)
- [Apple Metadata](docs/store/apple/metadata.json)
- [Google Listing](docs/store/google/listing.json)

---

*This report was automatically generated. Manual review is still recommended.*
"""

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        return report_path

    def run_all_checks(self):
        """Run all validation checks"""
        print("=" * 60)
        print("🔍 BabyShield Pre-Submission Validator")
        print("=" * 60)

        self.check_metadata_files()
        self.check_descriptions()
        self.check_assets()
        self.check_review_notes()
        self.check_bundle_identifiers()
        self.check_compliance()

        # Only check URLs if --check-urls flag is passed
        if "--check-urls" in sys.argv:
            self.check_urls()
            self.check_api_endpoints()
        else:
            print("\n🌐 Skipping URL checks (use --check-urls to enable)")

        # Generate report
        report_path = self.generate_submission_report()

        # Print summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"\n✅ Passed: {self.checks_passed}")
        print(f"❌ Failed: {self.checks_failed}")
        print(f"⚠️  Warnings: {len(self.warnings)}")

        if self.checks_failed == 0:
            print("\n🎉 SUCCESS! Your app is ready for submission!")
            print("\nNext steps:")
            print("1. Review the warnings above (if any)")
            print("2. Replace placeholder assets with real ones")
            print("3. Submit to app stores")
        else:
            print("\n⚠️  ATTENTION! Issues found that must be fixed.")
            print("\nRequired actions:")
            print("1. Fix all errors listed above")
            print("2. Re-run this validator")
            print("3. Ensure all checks pass")

        print(f"\n📄 Full report saved to: {report_path}")

        return 0 if self.checks_failed == 0 else 1


def main():
    """Main entry point"""
    validator = SubmissionValidator()
    return validator.run_all_checks()


if __name__ == "__main__":
    sys.exit(main())
