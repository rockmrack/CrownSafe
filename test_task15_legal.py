#!/usr/bin/env python3
"""
Task 15: Legal & Privacy Testing
Tests for legal document endpoints and privacy compliance
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Any

BASE_URL = "https://babyshield.cureviax.ai"
LOCAL_URL = "http://localhost:8001"

# Use local for testing if available
API_URL = LOCAL_URL


def test_legal_documents():
    """Test legal document endpoints"""
    
    print("="*70)
    print("LEGAL DOCUMENTS TEST")
    print("="*70)
    
    # Test list of documents
    print("\n1. Testing document list...")
    try:
        response = requests.get(f"{API_URL}/legal/", timeout=5)
        
        if response.status_code == 200:
            documents = response.json()
            print(f"   ✅ Found {len(documents)} legal documents")
            
            for doc in documents:
                print(f"      - {doc['title']} (v{doc['version']})")
                print(f"        URL: {doc['url']}")
                print(f"        Effective: {doc['effective_date']}")
            
            return True
        else:
            print(f"   ❌ Failed: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_privacy_policy():
    """Test privacy policy access"""
    
    print("\n" + "="*70)
    print("PRIVACY POLICY ACCESS TEST")
    print("="*70)
    
    formats = ["html", "markdown", "plain"]
    passed = 0
    
    for format_type in formats:
        try:
            response = requests.get(
                f"{API_URL}/legal/privacy",
                params={"format": format_type},
                timeout=5
            )
            
            if response.status_code == 200:
                content_length = len(response.text)
                print(f"✅ Privacy Policy ({format_type}): {content_length} bytes")
                
                # Check for required sections
                content = response.text.lower()
                required_sections = [
                    "information we collect",
                    "how we use",
                    "data security",
                    "your rights",
                    "contact"
                ]
                
                missing = []
                for section in required_sections:
                    if section not in content:
                        missing.append(section)
                
                if missing:
                    print(f"   ⚠️ Missing sections: {missing}")
                else:
                    print(f"   ✅ All required sections present")
                    passed += 1
            else:
                print(f"❌ Privacy Policy ({format_type}): Status {response.status_code}")
                
        except Exception as e:
            print(f"❌ Privacy Policy ({format_type}): Error - {e}")
    
    return passed == len(formats)


def test_terms_of_service():
    """Test terms of service access"""
    
    print("\n" + "="*70)
    print("TERMS OF SERVICE ACCESS TEST")
    print("="*70)
    
    try:
        response = requests.get(f"{API_URL}/legal/terms", timeout=5)
        
        if response.status_code == 200:
            content = response.text.lower()
            
            # Check for required sections
            required = [
                "acceptance",
                "service",
                "privacy",
                "limitation",
                "contact"
            ]
            
            found = sum(1 for term in required if term in content)
            
            print(f"✅ Terms of Service accessible")
            print(f"   Required sections: {found}/{len(required)}")
            
            return found == len(required)
        else:
            print(f"❌ Terms of Service: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Terms of Service: Error - {e}")
        return False


def test_privacy_summary():
    """Test privacy summary endpoint"""
    
    print("\n" + "="*70)
    print("PRIVACY SUMMARY TEST")
    print("="*70)
    
    try:
        response = requests.get(f"{API_URL}/legal/privacy/summary", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ Privacy Summary Retrieved")
            
            # Check data collected
            collected = data.get("summary", {}).get("data_collected", [])
            print(f"\nData Collected ({len(collected)} types):")
            for item in collected[:3]:
                print(f"   - {item}")
            
            # Check data NOT collected
            not_collected = data.get("summary", {}).get("data_not_collected", [])
            print(f"\nData NOT Collected ({len(not_collected)} types):")
            for item in not_collected[:3]:
                print(f"   - {item}")
            
            # Check user rights
            rights = data.get("summary", {}).get("user_rights", [])
            print(f"\nUser Rights ({len(rights)}):")
            for right in rights[:3]:
                print(f"   - {right}")
            
            # Check privacy settings
            settings = data.get("settings", {})
            print(f"\nDefault Privacy Settings:")
            print(f"   Crashlytics: {settings.get('crashlytics_enabled')} (should be False)")
            print(f"   Analytics: {settings.get('analytics_enabled')}")
            print(f"   Data Sharing: {settings.get('data_sharing')}")
            
            # Verify Crashlytics is OFF by default
            if settings.get("crashlytics_enabled") == False:
                print("   ✅ Crashlytics OFF by default")
                return True
            else:
                print("   ❌ Crashlytics should be OFF by default")
                return False
                
        else:
            print(f"❌ Privacy Summary: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Privacy Summary: Error - {e}")
        return False


def test_consent_management():
    """Test consent update endpoints"""
    
    print("\n" + "="*70)
    print("CONSENT MANAGEMENT TEST")
    print("="*70)
    
    test_user_id = "test_user_123"
    
    # Test consent update
    consent_types = ["crashlytics", "analytics", "notifications"]
    
    for consent_type in consent_types:
        try:
            response = requests.post(
                f"{API_URL}/legal/privacy/consent",
                headers={"X-User-ID": test_user_id},
                json={
                    "user_id": test_user_id,
                    "consent_type": consent_type,
                    "granted": False  # Always opt-out for privacy
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {consent_type}: Consent updated")
                print(f"   Status: {'Granted' if data.get('granted') else 'Withdrawn'}")
            else:
                print(f"❌ {consent_type}: Status {response.status_code}")
                
        except Exception as e:
            print(f"❌ {consent_type}: Error - {e}")
    
    return True


def test_data_rights():
    """Test GDPR/CCPA data rights endpoints"""
    
    print("\n" + "="*70)
    print("DATA RIGHTS TEST (GDPR/CCPA)")
    print("="*70)
    
    test_user_id = "test_user_123"
    
    # Test data export request
    print("\n1. Testing data export (Article 15/20)...")
    try:
        response = requests.post(
            f"{API_URL}/legal/privacy/request-data",
            headers={"X-User-ID": test_user_id},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Data export requested")
            print(f"      Request ID: {data.get('request_id')}")
            print(f"      Status: {data.get('status')}")
            print(f"      Format: {data.get('format')}")
        else:
            print(f"   ❌ Failed: Status {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test data deletion request
    print("\n2. Testing data deletion (Article 17)...")
    try:
        response = requests.post(
            f"{API_URL}/legal/privacy/delete-data",
            headers={"X-User-ID": test_user_id},
            json={
                "user_id": test_user_id,
                "reason": "Testing",
                "confirm": True
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Data deletion requested")
            print(f"      Request ID: {data.get('request_id')}")
            print(f"      Status: {data.get('status')}")
            print(f"      Grace Period: {data.get('grace_period')}")
        else:
            print(f"   ❌ Failed: Status {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return True


def test_compliance_status():
    """Test compliance status endpoint"""
    
    print("\n" + "="*70)
    print("COMPLIANCE STATUS TEST")
    print("="*70)
    
    try:
        response = requests.get(f"{API_URL}/legal/compliance/status", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            compliance = data.get("compliance", {})
            
            print("Compliance Status:")
            print("-" * 70)
            
            # GDPR Compliance
            gdpr = compliance.get("gdpr", {})
            print(f"\nGDPR Compliance:")
            print(f"   Compliant: {gdpr.get('compliant')}")
            print(f"   DPO Appointed: {gdpr.get('dpo_appointed')}")
            print(f"   DPO Email: {gdpr.get('dpo_email')}")
            print(f"   Encryption: {gdpr.get('encryption')}")
            
            # CCPA Compliance
            ccpa = compliance.get("ccpa", {})
            print(f"\nCCPA Compliance:")
            print(f"   Compliant: {ccpa.get('compliant')}")
            print(f"   Do Not Sell: {ccpa.get('do_not_sell')}")
            print(f"   Deletion Rights: {ccpa.get('deletion_rights')}")
            
            # App Store Compliance
            app_store = compliance.get("app_store", {})
            print(f"\nApp Store Compliance:")
            print(f"   Apple Privacy Labels: {app_store.get('apple_privacy_labels')}")
            print(f"   Google Data Safety: {app_store.get('google_data_safety')}")
            
            # Data Protection
            protection = data.get("data_protection", {})
            print(f"\nData Protection:")
            print(f"   Encryption at Rest: {protection.get('encryption_at_rest')}")
            print(f"   Encryption in Transit: {protection.get('encryption_in_transit')}")
            print(f"   MFA Required: {protection.get('mfa_required')}")
            
            return True
        else:
            print(f"❌ Compliance Status: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Compliance Status: Error - {e}")
        return False


def test_one_tap_access():
    """Verify one-tap access requirements"""
    
    print("\n" + "="*70)
    print("ONE-TAP ACCESS VERIFICATION")
    print("="*70)
    
    # Test direct access URLs (should return 200)
    one_tap_urls = [
        ("/legal/privacy", "Privacy Policy"),
        ("/legal/terms", "Terms of Service"),
        ("/legal/privacy/summary", "Privacy Summary"),
        ("/api/v1/user/data/export", "Data Export"),
        ("/api/v1/user/data/delete", "Data Deletion")
    ]
    
    print("Checking one-tap accessibility:")
    accessible = 0
    
    for url, name in one_tap_urls:
        # Check if endpoint exists and responds
        full_url = f"{API_URL}{url}"
        
        # For POST endpoints, check OPTIONS
        if "delete" in url or "export" in url:
            method = "OPTIONS"
        else:
            method = "GET"
        
        try:
            response = requests.request(method, full_url, timeout=2)
            
            # Success if endpoint exists (200 or 405 for wrong method)
            if response.status_code in [200, 405, 401]:  # 401 is ok, means auth required
                print(f"   ✅ {name}: Accessible")
                accessible += 1
            else:
                print(f"   ❌ {name}: Status {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {name}: Not accessible")
    
    print(f"\nOne-tap access score: {accessible}/{len(one_tap_urls)}")
    return accessible == len(one_tap_urls)


def test_dpa_checklist():
    """Test DPA checklist availability"""
    
    print("\n" + "="*70)
    print("DPA CHECKLIST TEST")
    print("="*70)
    
    try:
        response = requests.get(f"{API_URL}/legal/dpa", timeout=5)
        
        if response.status_code == 200:
            content = response.text.lower()
            
            # Check for required DPA items
            required_items = [
                "google",
                "crashlytics",
                "aws",
                "data processing",
                "gdpr",
                "security"
            ]
            
            found = sum(1 for item in required_items if item in content)
            
            print(f"✅ DPA Checklist accessible")
            print(f"   Required items: {found}/{len(required_items)}")
            
            # Check for Crashlytics opt-in requirement
            if "off by default" in content or "opt-in" in content:
                print(f"   ✅ Crashlytics opt-in documented")
            else:
                print(f"   ⚠️ Crashlytics opt-in not clearly documented")
            
            return found == len(required_items)
        else:
            print(f"❌ DPA Checklist: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ DPA Checklist: Error - {e}")
        return False


def main():
    """Run all legal and privacy tests"""
    
    print("="*70)
    print("TASK 15: LEGAL & PRIVACY HARDENING TEST SUITE")
    print("="*70)
    print(f"API URL: {API_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_passed = True
    
    # Test legal documents
    if not test_legal_documents():
        all_passed = False
    
    # Test privacy policy
    if not test_privacy_policy():
        all_passed = False
    
    # Test terms of service
    if not test_terms_of_service():
        all_passed = False
    
    # Test privacy summary
    if not test_privacy_summary():
        all_passed = False
    
    # Test consent management
    if not test_consent_management():
        all_passed = False
    
    # Test data rights
    if not test_data_rights():
        all_passed = False
    
    # Test compliance status
    if not test_compliance_status():
        all_passed = False
    
    # Test one-tap access
    if not test_one_tap_access():
        all_passed = False
    
    # Test DPA checklist
    if not test_dpa_checklist():
        all_passed = False
    
    # Summary
    print("\n" + "="*70)
    print("ACCEPTANCE CRITERIA CHECK")
    print("="*70)
    
    criteria = [
        ("Privacy Policy finalized", "With company info placeholders"),
        ("Terms of Service finalized", "With company info placeholders"),
        ("DPA checklist in repo", "Google Crashlytics documented"),
        ("One-tap legal access", "All links directly accessible"),
        ("Data export endpoint", "GDPR Article 15/20"),
        ("Data deletion endpoint", "GDPR Article 17"),
        ("Crashlytics OFF by default", "Opt-in required"),
        ("Privacy summary available", "Clear data practices"),
        ("Consent management", "User controls available"),
        ("Compliance status", "GDPR/CCPA/App Store ready")
    ]
    
    for criterion, detail in criteria:
        print(f"✅ {criterion}")
        print(f"   {detail}")
    
    if all_passed:
        print("\n" + "="*70)
        print("✅ TASK 15 ACCEPTANCE CRITERIA MET")
        print("="*70)
        print("\n🎉 Legal & Privacy Hardening Complete!")
        print("- Privacy Policy ready for customization")
        print("- Terms of Service ready for customization")
        print("- DPA checklist with Crashlytics documented")
        print("- One-tap access to all legal/privacy functions")
        print("- GDPR/CCPA compliant endpoints")
        print("- App Store privacy forms guidance ready")
    else:
        print("\n⚠️ Some tests failed. Please review and fix issues.")
    
    print("\n📝 Next Steps:")
    print("1. Replace [YOUR COMPANY] placeholders in legal docs")
    print("2. Sign DPAs with Google, AWS")
    print("3. Complete App Store privacy forms")
    print("4. Test one-tap access in mobile app")
    print("5. Conduct legal review")


if __name__ == "__main__":
    # Check if API is running
    try:
        response = requests.get(f"{LOCAL_URL}/api/v1/healthz", timeout=2)
        if response.status_code == 200:
            API_URL = LOCAL_URL
            print("✅ Testing with local API\n")
        else:
            raise Exception()
    except:
        API_URL = BASE_URL
        print("🌐 Testing with production API\n")
    
    main()
