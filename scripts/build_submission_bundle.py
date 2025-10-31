#!/usr/bin/env python3
"""Build store submission bundle (ZIP) with all required assets and documents."""

import json
import os
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(__file__))
OUTDIR = os.path.join(ROOT, "dist")
STAMP = time.strftime("%Y%m%d-%H%M%S")
ZIPNAME = f"babyshield_store_pack_{STAMP}.zip"

INCLUDE = [
    # Apple Store docs
    "docs/store/apple/metadata.json",
    "docs/store/apple/review_notes.md",
    "docs/store/apple/screenshots_checklist.md",
    "docs/store/apple/export_compliance.md",
    # Google Play docs
    "docs/store/google/listing.json",
    "docs/store/google/review_notes.md",
    "docs/store/google/screenshots_checklist.md",
    # Common descriptions
    "docs/store/common/descriptions/short_tagline.txt",
    "docs/store/common/descriptions/long_description_en.txt",
    # Privacy docs
    "docs/app_review/privacy_labels_apple.json",
    "docs/app_review/google_data_safety.json",
    "docs/app_review/support_contacts.md",
    "docs/app_review/age_rating_apple.md",
    # API documentation
    "docs/api/openapi_v1.yaml",
    "docs/api/openapi_v1.yml",
    "docs/api/openapi_v1.json",
    "docs/api/postman/BabyShield_v1.postman_collection.json",
    "docs/api/README.md",
    # Store guides
    "docs/store/REQUIRED_ASSETS.md",
    "docs/store/SUBMISSION_CHECKLIST.md",
    "docs/store/SCREENSHOT_CAPTURE_GUIDE.md",
]

ASSETS = [
    # Critical assets (icons and feature graphic)
    "assets/store/icons/ios/AppIcon1024.png",
    "assets/store/icons/android/Icon512.png",
    "assets/store/graphics/play-feature-1024x500.png",
    # iOS screenshots
    "assets/store/screenshots/ios/iphone67-01-home.png",
    "assets/store/screenshots/ios/iphone67-02-search.png",
    "assets/store/screenshots/ios/iphone67-03-scanner.png",
    "assets/store/screenshots/ios/iphone67-04-detail.png",
    "assets/store/screenshots/ios/iphone67-05-settings.png",
    "assets/store/screenshots/ios/iphone65-01-home.png",
    "assets/store/screenshots/ios/iphone65-02-search.png",
    "assets/store/screenshots/ios/iphone65-03-scanner.png",
    # Android screenshots
    "assets/store/screenshots/android/phone-01-home.png",
    "assets/store/screenshots/android/phone-02-search.png",
    "assets/store/screenshots/android/phone-03-scanner.png",
    "assets/store/screenshots/android/phone-04-detail.png",
    "assets/store/screenshots/android/phone-05-settings.png",
]


def main() -> int:
    """Build the submission bundle."""
    print("📦 Building store submission bundle...")
    print("=" * 60)

    # Create output directory
    os.makedirs(OUTDIR, exist_ok=True)
    zpath = os.path.join(OUTDIR, ZIPNAME)

    added = 0
    missing_docs = []
    missing_assets = []
    missing_critical = []

    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # Include docs (only if file exists)
        print("\n📄 Adding documentation files...")
        for rel in INCLUDE:
            p = os.path.join(ROOT, rel)
            if os.path.exists(p):
                z.write(p, arcname=rel)
                added += 1
                print(f"  ✅ {rel}")
            else:
                missing_docs.append(rel)
                print(f"  ⚠️  Missing: {rel}")

        # Include assets if present; warn if critical ones missing
        print("\n🎨 Adding asset files...")
        for rel in ASSETS:
            p = os.path.join(ROOT, rel)
            if os.path.exists(p):
                # Check if it's a placeholder
                if os.path.getsize(p) < 1000:  # Less than 1KB likely a placeholder
                    with open(p, "rb") as f:
                        content = f.read()
                        if b"PLACEHOLDER" in content:
                            print(f"  ⚠️  Placeholder detected: {rel}")
                            missing_assets.append(rel + " (placeholder)")
                z.write(p, arcname=rel)
                added += 1
                print(f"  ✅ {rel}")
            else:
                missing_assets.append(rel)
                print(f"  ⚠️  Missing: {rel}")

                # Check if critical asset
                if (
                    rel.endswith("AppIcon1024.png")
                    or rel.endswith("Icon512.png")
                    or rel.endswith("play-feature-1024x500.png")
                ):
                    missing_critical.append(rel)

        # Write a manifest
        manifest = {
            "created": STAMP,
            "files_included": added,
            "missing_docs": missing_docs,
            "missing_assets": missing_assets,
            "missing_critical_assets": missing_critical,
            "bundle_name": ZIPNAME,
            "notes": "Replace placeholder images with actual screenshots before submission",
        }

        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        print("\n📋 Added manifest.json")

    print("\n" + "=" * 60)
    print(f"📦 Built: {zpath}")
    print(f"📊 Files included: {added}")

    if missing_docs:
        print(f"\n⚠️  Missing {len(missing_docs)} documentation files")

    if missing_assets:
        print(f"\n⚠️  Missing {len(missing_assets)} asset files")

    if missing_critical:
        print("\n❌ CRITICAL: Missing required assets:")
        for m in missing_critical:
            print(f"   - {m}")
        print("\n⚠️  The bundle was created but is incomplete!")
        print("   You must add the critical assets before submission.")
        return 2  # Exit with error code

    print("\n✅ Bundle created successfully!")
    print(f"   Location: {zpath}")
    print(f"   Size: {os.path.getsize(zpath) / 1024 / 1024:.2f} MB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
