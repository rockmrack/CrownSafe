#!/usr/bin/env python3
"""BabyShield Store Asset Generator & Validator
Creates placeholder assets and validates existing ones for app store submission.
"""

import sys
from datetime import datetime
from pathlib import Path

# Asset specifications
ASSET_SPECS = {
    "ios": {
        "icon": {"AppIcon1024.png": (1024, 1024, "PNG", "App Store icon - no alpha")},
        "screenshots": {
            "iphone67": {
                "size": (1290, 2796),
                "required": 5,
                "names": ["home", "search", "scanner", "detail", "settings"],
            },
            "iphone65": {
                "size": (1242, 2688),
                "required": 3,
                "names": ["home", "search", "scanner"],
            },
            "iphone55": {"size": (1242, 2208), "required": 0, "names": []},
            "ipad129": {"size": (2048, 2732), "required": 0, "names": []},
        },
    },
    "android": {
        "icon": {"Icon512.png": (512, 512, "PNG", "Play Store icon - with alpha")},
        "graphics": {"play-feature-1024x500.png": (1024, 500, "PNG/JPG", "Feature graphic")},
        "screenshots": {
            "phone": {
                "size": (1080, 1920),  # Minimum size
                "required": 5,
                "names": ["home", "search", "scanner", "detail", "settings"],
            },
            "tablet7": {"size": (1200, 1920), "required": 0, "names": []},
            "tablet10": {"size": (1600, 2560), "required": 0, "names": []},
        },
    },
}


class AssetGenerator:
    def __init__(self, base_path: str = ".") -> None:
        self.base_path = Path(base_path)
        self.assets_path = self.base_path / "assets" / "store"
        self.report = {"created": [], "existing": [], "missing": [], "errors": []}

    def create_directories(self) -> None:
        """Create all necessary asset directories."""
        dirs = [
            self.assets_path / "icons" / "ios",
            self.assets_path / "icons" / "android",
            self.assets_path / "screenshots" / "ios",
            self.assets_path / "screenshots" / "android",
            self.assets_path / "graphics",
        ]

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Directory: {dir_path}")

    def create_placeholder_image(self, path: Path, size: tuple[int, int], text: str):
        """Create a placeholder image file with specifications."""
        content = f"""PLACEHOLDER IMAGE
Size: {size[0]}x{size[1]}
Purpose: {text}
Created: {datetime.now().isoformat()}

TO REPLACE:
1. Create actual image at {size[0]}x{size[1]} pixels
2. Save as PNG (or JPG for Android feature graphic)
3. Replace this file at: {path}

DESIGN GUIDELINES:
- Use brand colors: #667EEA (primary), #48BB78 (secondary)
- Include app logo
- Show actual app UI (not mockups)
- Ensure text is readable
- Follow platform guidelines
"""

        path.write_text(content)
        return path

    def generate_ios_assets(self) -> None:
        """Generate iOS asset placeholders."""
        print("\n📱 iOS Assets:")

        # App icon
        icon_path = self.assets_path / "icons" / "ios" / "AppIcon1024.png"
        if not icon_path.exists():
            self.create_placeholder_image(icon_path, (1024, 1024), "iOS App Store Icon")
            self.report["created"].append(str(icon_path))
            print(f"  ✓ Created: {icon_path.name}")
        else:
            self.report["existing"].append(str(icon_path))
            print(f"  • Exists: {icon_path.name}")

        # Screenshots
        for device, specs in ASSET_SPECS["ios"]["screenshots"].items():
            for i, name in enumerate(specs["names"], 1):
                filename = f"{device}-{i:02d}-{name}.png"
                path = self.assets_path / "screenshots" / "ios" / filename

                if not path.exists():
                    self.create_placeholder_image(path, specs["size"], f"iOS {device} - {name.title()} Screen")
                    self.report["created"].append(str(path))
                    print(f"  ✓ Created: {filename}")
                else:
                    self.report["existing"].append(str(path))
                    print(f"  • Exists: {filename}")

    def generate_android_assets(self) -> None:
        """Generate Android asset placeholders."""
        print("\n🤖 Android Assets:")

        # App icon
        icon_path = self.assets_path / "icons" / "android" / "Icon512.png"
        if not icon_path.exists():
            self.create_placeholder_image(icon_path, (512, 512), "Android Play Store Icon")
            self.report["created"].append(str(icon_path))
            print(f"  ✓ Created: {icon_path.name}")
        else:
            self.report["existing"].append(str(icon_path))
            print(f"  • Exists: {icon_path.name}")

        # Feature graphic
        feature_path = self.assets_path / "graphics" / "play-feature-1024x500.png"
        if not feature_path.exists():
            self.create_placeholder_image(feature_path, (1024, 500), "Play Store Feature Graphic")
            self.report["created"].append(str(feature_path))
            print(f"  ✓ Created: {feature_path.name}")
        else:
            self.report["existing"].append(str(feature_path))
            print(f"  • Exists: {feature_path.name}")

        # Screenshots
        for device, specs in ASSET_SPECS["android"]["screenshots"].items():
            for i, name in enumerate(specs["names"], 1):
                filename = f"{device}-{i:02d}-{name}.png"
                path = self.assets_path / "screenshots" / "android" / filename

                if not path.exists():
                    self.create_placeholder_image(
                        path,
                        specs["size"],
                        f"Android {device.title()} - {name.title()} Screen",
                    )
                    self.report["created"].append(str(path))
                    print(f"  ✓ Created: {filename}")
                else:
                    self.report["existing"].append(str(path))
                    print(f"  • Exists: {filename}")

    def validate_assets(self):
        """Validate that all required assets exist."""
        print("\n🔍 Validating Assets:")

        all_valid = True

        # Check iOS requirements
        print("\niOS Requirements:")
        if not (self.assets_path / "icons" / "ios" / "AppIcon1024.png").exists():
            print("  ❌ Missing: AppIcon1024.png")
            self.report["missing"].append("iOS App Icon")
            all_valid = False
        else:
            print("  ✓ App Icon present")

        # Check required iOS screenshots
        iphone67_count = len(list((self.assets_path / "screenshots" / "ios").glob("iphone67-*.png")))
        iphone65_count = len(list((self.assets_path / "screenshots" / "ios").glob("iphone65-*.png")))

        if iphone67_count < 3:
            print(f'  ❌ iPhone 6.7" screenshots: {iphone67_count}/3 minimum')
            self.report["missing"].append(f'iPhone 6.7" screenshots ({3 - iphone67_count} more needed)')
            all_valid = False
        else:
            print(f'  ✓ iPhone 6.7" screenshots: {iphone67_count}')

        if iphone65_count < 3:
            print(f'  ❌ iPhone 6.5" screenshots: {iphone65_count}/3 minimum')
            self.report["missing"].append(f'iPhone 6.5" screenshots ({3 - iphone65_count} more needed)')
            all_valid = False
        else:
            print(f'  ✓ iPhone 6.5" screenshots: {iphone65_count}')

        # Check Android requirements
        print("\nAndroid Requirements:")
        if not (self.assets_path / "icons" / "android" / "Icon512.png").exists():
            print("  ❌ Missing: Icon512.png")
            self.report["missing"].append("Android App Icon")
            all_valid = False
        else:
            print("  ✓ App Icon present")

        if not (self.assets_path / "graphics" / "play-feature-1024x500.png").exists():
            print("  ❌ Missing: Feature Graphic")
            self.report["missing"].append("Android Feature Graphic")
            all_valid = False
        else:
            print("  ✓ Feature Graphic present")

        phone_count = len(list((self.assets_path / "screenshots" / "android").glob("phone-*.png")))
        if phone_count < 2:
            print(f"  ❌ Phone screenshots: {phone_count}/2 minimum")
            self.report["missing"].append(f"Android phone screenshots ({2 - phone_count} more needed)")
            all_valid = False
        else:
            print(f"  ✓ Phone screenshots: {phone_count}")

        return all_valid

    def generate_html_preview(self):
        """Generate an HTML file to preview all assets."""
        html = (
            """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BabyShield Store Assets Preview</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1, h2, h3 {
            color: #2D3748;
        }
        .platform {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .asset-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .asset-item {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        .asset-placeholder {
            background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%);
            color: white;
            padding: 40px 20px;
            border-radius: 8px;
            min-height: 150px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }
        .asset-name {
            font-weight: bold;
            margin-top: 10px;
            color: #4A5568;
        }
        .asset-size {
            color: #718096;
            font-size: 0.875rem;
        }
        .status {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
            margin-top: 5px;
        }
        .status.exists {
            background: #C6F6D5;
            color: #22543D;
        }
        .status.placeholder {
            background: #FED7D7;
            color: #742A2A;
        }
        .checklist {
            background: #EDF2F7;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
        }
        .checklist li {
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <h1>🚀 BabyShield Store Assets Preview</h1>
    <p>Generated: """
            + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            + """</p>
    
    <div class="platform">
        <h2>📱 iOS Assets</h2>
        
        <h3>App Icon</h3>
        <div class="asset-item">
            <div class="asset-placeholder">
                <div>App Icon</div>
                <div class="asset-size">1024x1024</div>
            </div>
            <div class="asset-name">AppIcon1024.png</div>
            <div class="status placeholder">Placeholder</div>
        </div>
        
        <h3>Screenshots</h3>
        <div class="asset-grid">
            <div class="asset-item">
                <div class="asset-placeholder">
                    <div>iPhone 6.7"</div>
                    <div class="asset-size">1290x2796</div>
                </div>
                <div class="asset-name">Home Screen</div>
                <div class="status placeholder">Required</div>
            </div>
            <div class="asset-item">
                <div class="asset-placeholder">
                    <div>iPhone 6.7"</div>
                    <div class="asset-size">1290x2796</div>
                </div>
                <div class="asset-name">Search Results</div>
                <div class="status placeholder">Required</div>
            </div>
            <div class="asset-item">
                <div class="asset-placeholder">
                    <div>iPhone 6.7"</div>
                    <div class="asset-size">1290x2796</div>
                </div>
                <div class="asset-name">Barcode Scanner</div>
                <div class="status placeholder">Required</div>
            </div>
        </div>
    </div>
    
    <div class="platform">
        <h2>🤖 Android Assets</h2>
        
        <h3>App Icon</h3>
        <div class="asset-item">
            <div class="asset-placeholder">
                <div>App Icon</div>
                <div class="asset-size">512x512</div>
            </div>
            <div class="asset-name">Icon512.png</div>
            <div class="status placeholder">Placeholder</div>
        </div>
        
        <h3>Feature Graphic</h3>
        <div class="asset-item">
            <div class="asset-placeholder">
                <div>Feature Graphic</div>
                <div class="asset-size">1024x500</div>
            </div>
            <div class="asset-name">play-feature-1024x500.png</div>
            <div class="status placeholder">Placeholder</div>
        </div>
        
        <h3>Screenshots</h3>
        <div class="asset-grid">
            <div class="asset-item">
                <div class="asset-placeholder">
                    <div>Phone</div>
                    <div class="asset-size">1080x1920+</div>
                </div>
                <div class="asset-name">Home Screen</div>
                <div class="status placeholder">Required</div>
            </div>
            <div class="asset-item">
                <div class="asset-placeholder">
                    <div>Phone</div>
                    <div class="asset-size">1080x1920+</div>
                </div>
                <div class="asset-name">Search Results</div>
                <div class="status placeholder">Required</div>
            </div>
        </div>
    </div>
    
    <div class="platform">
        <h2>✅ Asset Checklist</h2>
        <div class="checklist">
            <ul>
                <li>☐ Replace all placeholder images with actual screenshots</li>
                <li>☐ Ensure iOS app icon has no transparency</li>
                <li>☐ Ensure Android icon includes alpha channel</li>
                <li>☐ Verify all images are correct dimensions</li>
                <li>☐ Include actual app UI (not mockups)</li>
                <li>☐ Show key features in screenshots</li>
                <li>☐ Add app branding to feature graphic</li>
                <li>☐ Test images in store preview tools</li>
                <li>☐ Ensure text is readable at all sizes</li>
                <li>☐ Remove any personal information</li>
            </ul>
        </div>
    </div>
</body>
</html>"""
        )

        preview_path = self.base_path / "assets_preview.html"
        preview_path.write_text(html, encoding="utf-8")
        print(f"\n📄 Preview generated: {preview_path}")
        return preview_path

    def print_summary(self) -> None:
        """Print a summary report."""
        print("\n" + "=" * 60)
        print("📊 ASSET GENERATION SUMMARY")
        print("=" * 60)

        print(f"\n✅ Created: {len(self.report['created'])} placeholder files")
        for path in self.report["created"][:5]:
            print(f"   • {Path(path).name}")
        if len(self.report["created"]) > 5:
            print(f"   ... and {len(self.report['created']) - 5} more")

        if self.report["existing"]:
            print(f"\n📁 Already exists: {len(self.report['existing'])} files")

        if self.report["missing"]:
            print(f"\n❌ Still missing: {len(self.report['missing'])} required assets")
            for item in self.report["missing"]:
                print(f"   • {item}")

        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print(
            """
1. REPLACE PLACEHOLDERS:
   • Open each .png placeholder file
   • Follow instructions inside each file
   • Replace with actual screenshots/icons

2. CREATE SCREENSHOTS:
   • Use actual app running on device/simulator
   • Capture at exact dimensions specified
   • Show key features: search, scan, results, settings

3. DESIGN ICONS:
   • iOS: 1024x1024 PNG, no transparency
   • Android: 512x512 PNG, with transparency

4. VALIDATE:
   • Run this script again with --validate flag
   • Ensure all requirements are met

5. OPTIMIZE:
   • Compress images (keep under 1MB for icons)
   • Use proper color profiles (sRGB)
   • Test in store preview tools
        """,
        )


def main() -> int:
    """Main entry point."""
    print("🎨 BabyShield Store Asset Generator")
    print("=" * 60)

    generator = AssetGenerator()

    # Parse arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--validate":
        # Validation mode
        print("Running in VALIDATION mode\n")
        is_valid = generator.validate_assets()
        if is_valid:
            print("\n✅ All required assets are present!")
        else:
            print("\n❌ Some required assets are missing. Generate placeholders first.")
        return 0 if is_valid else 1
    # Generation mode
    print("Running in GENERATION mode\n")

    # Create directory structure
    print("📁 Creating directory structure...")
    generator.create_directories()

    # Generate assets
    generator.generate_ios_assets()
    generator.generate_android_assets()

    # Validate what we have
    generator.validate_assets()

    # Generate preview
    generator.generate_html_preview()

    # Print summary
    generator.print_summary()

    return 0


if __name__ == "__main__":
    sys.exit(main())
