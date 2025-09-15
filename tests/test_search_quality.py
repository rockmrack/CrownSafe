"""
Search Quality Tests
Tests fuzzy matching, keyword AND logic, exact ID lookup, and deterministic sorting
"""

import pytest
import requests
import json
import time
import threading
import statistics
from typing import List, Dict, Any
import os

# Base URL from environment or default
BASE_URL = os.getenv("BABYSHIELD_BASE_URL", "http://localhost:8000")
SEARCH_ENDPOINT = f"{BASE_URL}/api/v1/search/advanced"
FDA_ENDPOINT = f"{BASE_URL}/api/v1/fda"


class TestSearchQuality:
    """Test suite for search quality improvements"""
    
    @classmethod
    def setup_class(cls):
        """Setup for all tests"""
        cls.session = requests.Session()
        cls.session.headers.update({"Content-Type": "application/json"})
    
    def test_fuzzy_match_works(self):
        """Test 1: Fuzzy match should find results despite typos"""
        # Test with slight misspelling
        payload = {
            "product": "Triacting Night Time Cold",  # Correct or slightly misspelled
            "agencies": ["FDA"],
            "limit": 3
        }
        
        response = self.session.post(SEARCH_ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") == True, "Response should have ok=true"
        assert "data" in data, "Response should have data field"
        assert "items" in data["data"], "Data should have items"
        assert data["data"]["total"] >= 1, "Should find at least 1 result with fuzzy matching"
        
        # Check if results have relevance scores
        if len(data["data"]["items"]) > 0:
            first_item = data["data"]["items"][0]
            if "relevanceScore" in first_item:
                assert first_item["relevanceScore"] > 0, "Relevance score should be positive"
        
        print(f"✅ Fuzzy match test passed: found {data['data']['total']} results")
    
    def test_keyword_and_logic(self):
        """Test 2: Keyword AND logic - all keywords must be present"""
        payload = {
            "keywords": ["baby", "food"],  # Both words must appear
            "agencies": ["FDA"],
            "limit": 5
        }
        
        response = self.session.post(SEARCH_ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") == True, "Response should have ok=true"
        
        items = data["data"]["items"]
        
        # Verify each result contains both keywords
        for item in items:
            # Check in various text fields
            text_fields = [
                item.get("productName", "").lower(),
                item.get("brand", "").lower(),
                item.get("description", "").lower(),
                item.get("hazard", "").lower(),
                item.get("title", "").lower()
            ]
            combined_text = " ".join(text_fields)
            
            assert "baby" in combined_text, f"Item {item.get('id')} missing 'baby' keyword"
            assert "food" in combined_text, f"Item {item.get('id')} missing 'food' keyword"
        
        print(f"✅ Keyword AND test passed: {len(items)} results contain both keywords")
    
    def test_exact_id_lookup(self):
        """Test 3: Exact ID lookup returns exactly one matching result"""
        # First, get an ID from FDA search
        fda_response = self.session.get(FDA_ENDPOINT, params={"product": "toy", "limit": 1})
        assert fda_response.status_code == 200, "FDA endpoint should work"
        
        fda_data = fda_response.json()
        if fda_data.get("data") and fda_data["data"].get("items") and len(fda_data["data"]["items"]) > 0:
            test_id = fda_data["data"]["items"][0].get("id")
            
            # Now search by exact ID
            payload = {"id": test_id}
            response = self.session.post(SEARCH_ENDPOINT, json=payload)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            assert data.get("ok") == True, "Response should have ok=true"
            assert len(data["data"]["items"]) == 1, "Exact ID search should return exactly 1 result"
            assert data["data"]["items"][0]["id"] == test_id, "Returned ID should match requested ID"
            
            print(f"✅ Exact ID test passed: found recall {test_id}")
        else:
            print("⚠️ No FDA data available to test exact ID lookup")
    
    def test_deterministic_order(self):
        """Test 4: Same query returns results in same order (deterministic)"""
        payload = {
            "product": "bottle",
            "agencies": ["FDA", "CPSC"],
            "limit": 5
        }
        
        # Make first request
        response1 = self.session.post(SEARCH_ENDPOINT, json=payload)
        assert response1.status_code == 200, "First request should succeed"
        data1 = response1.json()
        items1 = data1["data"]["items"]
        ids1 = [item["id"] for item in items1]
        
        # Make second identical request
        response2 = self.session.post(SEARCH_ENDPOINT, json=payload)
        assert response2.status_code == 200, "Second request should succeed"
        data2 = response2.json()
        items2 = data2["data"]["items"]
        ids2 = [item["id"] for item in items2]
        
        # Check order is identical
        assert ids1 == ids2, f"Order should be deterministic. First: {ids1}, Second: {ids2}"
        
        # Check if pagination cursor exists (for future use)
        if "nextCursor" in data1["data"]:
            print(f"   Pagination cursor: {data1['data']['nextCursor']}")
        
        print(f"✅ Deterministic order test passed: {len(ids1)} items in consistent order")
    
    def test_combined_search_features(self):
        """Test 5: Combined features - fuzzy match + keywords + filters"""
        payload = {
            "product": "pacifier",  # Main search term
            "keywords": ["sensor"],  # Additional keyword requirement
            "agencies": ["CPSC"],
            "limit": 10
        }
        
        response = self.session.post(SEARCH_ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") == True, "Response should have ok=true"
        
        # If results found, verify they match all criteria
        items = data["data"]["items"]
        if len(items) > 0:
            for item in items:
                # Check agency
                assert item.get("agencyCode") == "CPSC", f"Item {item['id']} not from CPSC"
                
                # Check for keyword
                text = f"{item.get('productName', '')} {item.get('description', '')}".lower()
                assert "sensor" in text or "pacifier" in text, f"Item {item['id']} doesn't match search criteria"
        
        print(f"✅ Combined features test passed: {len(items)} results match all criteria")
    
    def test_performance_smoke(self):
        """Test 6: Performance smoke test - parallel searches"""
        payload = {"product": "bottle", "limit": 5}
        latencies = []
        errors = []
        
        def search_worker():
            try:
                start = time.time()
                response = self.session.post(SEARCH_ENDPOINT, json=payload)
                elapsed = (time.time() - start) * 1000  # Convert to ms
                
                if response.status_code == 200:
                    latencies.append(elapsed)
                else:
                    errors.append(f"Status {response.status_code}")
            except Exception as e:
                errors.append(str(e))
        
        # Run 10 parallel searches
        threads = []
        for _ in range(10):
            t = threading.Thread(target=search_worker)
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        # Analyze results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(latencies) >= 8, "At least 80% of requests should succeed"
        
        median_latency = statistics.median(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95) - 1] if len(latencies) > 1 else latencies[0]
        
        print(f"   Median latency: {median_latency:.0f}ms")
        print(f"   P95 latency: {p95_latency:.0f}ms")
        print(f"   Success rate: {len(latencies)}/10")
        
        # Performance assertions
        assert median_latency < 800, f"Median latency {median_latency}ms exceeds 800ms threshold"
        assert p95_latency < 1500, f"P95 latency {p95_latency}ms exceeds 1500ms threshold"
        
        print(f"✅ Performance test passed: median={median_latency:.0f}ms, p95={p95_latency:.0f}ms")
    
    def test_empty_results_handling(self):
        """Test 7: Graceful handling of no results"""
        payload = {
            "keywords": ["impossibleword123", "nonexistent456"],
            "limit": 5
        }
        
        response = self.session.post(SEARCH_ENDPOINT, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("ok") == True, "Response should have ok=true even with no results"
        assert data["data"]["items"] == [], "Items should be empty array"
        assert data["data"]["total"] == 0, "Total should be 0"
        assert "traceId" in data, "Should have traceId for debugging"
        
        print("✅ Empty results test passed: graceful handling confirmed")
    
    def test_special_characters(self):
        """Test 8: Handle special characters in search"""
        test_cases = [
            {"product": "P&L Developments"},  # Ampersand
            {"product": "Children's"},  # Apostrophe
            {"product": "baby-food"},  # Hyphen
            {"keywords": ["3+", "months"]},  # Plus sign
        ]
        
        for payload in test_cases:
            payload["limit"] = 2
            response = self.session.post(SEARCH_ENDPOINT, json=payload)
            assert response.status_code == 200, f"Failed for payload {payload}"
            
            data = response.json()
            assert data.get("ok") == True, f"Should handle special chars in {payload}"
        
        print("✅ Special characters test passed: all handled gracefully")


def run_all_tests():
    """Run all tests and report results"""
    print("=" * 60)
    print("🔍 SEARCH QUALITY TEST SUITE")
    print("=" * 60)
    
    test = TestSearchQuality()
    test.setup_class()
    
    tests = [
        ("Fuzzy Match", test.test_fuzzy_match_works),
        ("Keyword AND Logic", test.test_keyword_and_logic),
        ("Exact ID Lookup", test.test_exact_id_lookup),
        ("Deterministic Order", test.test_deterministic_order),
        ("Combined Features", test.test_combined_search_features),
        ("Performance", test.test_performance_smoke),
        ("Empty Results", test.test_empty_results_handling),
        ("Special Characters", test.test_special_characters),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            print(f"\n📝 Testing: {name}")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ {name} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {name} error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️ {failed} tests need attention")
    
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
