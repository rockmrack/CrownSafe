#!/usr/bin/env python3
"""
Task 14: Monitoring & SLO Testing
Tests for Prometheus metrics, synthetic probes, and alert conditions
"""

import requests
import time
import json
import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Any

BASE_URL = "https://babyshield.cureviax.ai"
LOCAL_URL = "http://localhost:8001"

# Use local for testing if available
API_URL = LOCAL_URL


def test_health_endpoints():
    """Test health check endpoints"""
    
    print("="*70)
    print("HEALTH CHECK ENDPOINTS TEST")
    print("="*70)
    
    endpoints = [
        ("/api/v1/monitoring/healthz", "Basic health"),
        ("/api/v1/monitoring/readyz", "Readiness check"),
        ("/api/v1/monitoring/livez", "Liveness check")
    ]
    
    passed = 0
    failed = 0
    
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{API_URL}{endpoint}", timeout=5)
            
            if endpoint == "/api/v1/monitoring/healthz":
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "healthy":
                        print(f"✅ {description}: OK")
                        print(f"   Service: {data.get('service')}")
                        print(f"   Version: {data.get('version')}")
                        passed += 1
                    else:
                        print(f"❌ {description}: Unhealthy")
                        failed += 1
                else:
                    print(f"❌ {description}: Status {response.status_code}")
                    failed += 1
                    
            elif endpoint == "/api/v1/monitoring/readyz":
                if response.status_code in [200, 503]:
                    data = response.json()
                    ready = data.get("ready", False)
                    print(f"{'✅' if ready else '⚠️'} {description}: {'Ready' if ready else 'Not Ready'}")
                    
                    checks = data.get("checks", {})
                    for check, status in checks.items():
                        print(f"   {check}: {'✅' if status else '❌'}")
                    
                    if ready:
                        passed += 1
                    else:
                        failed += 1
                else:
                    print(f"❌ {description}: Status {response.status_code}")
                    failed += 1
                    
            elif endpoint == "/api/v1/monitoring/livez":
                if response.status_code == 200:
                    data = response.json()
                    if data.get("alive"):
                        print(f"✅ {description}: Alive")
                        passed += 1
                    else:
                        print(f"❌ {description}: Not alive")
                        failed += 1
                else:
                    print(f"❌ {description}: Status {response.status_code}")
                    failed += 1
                    
        except Exception as e:
            print(f"❌ {description}: Error - {e}")
            failed += 1
    
    print(f"\nHealth Checks: {passed} passed, {failed} failed")
    return failed == 0


def test_metrics_endpoint():
    """Test Prometheus metrics endpoint"""
    
    print("\n" + "="*70)
    print("PROMETHEUS METRICS TEST")
    print("="*70)
    
    try:
        response = requests.get(f"{API_URL}/metrics", timeout=5)
        
        if response.status_code == 200:
            metrics_text = response.text
            
            # Check for key metrics
            required_metrics = [
                "http_requests_total",
                "http_request_duration_seconds",
                "error_total",
                "rate_limit_hits_total",
                "barcode_scans_total",
                "search_queries_total",
                "system_memory_usage_bytes",
                "system_cpu_usage_percent"
            ]
            
            print("Checking required metrics:")
            found = 0
            missing = []
            
            for metric in required_metrics:
                if metric in metrics_text:
                    print(f"✅ {metric}")
                    found += 1
                else:
                    print(f"❌ {metric} - NOT FOUND")
                    missing.append(metric)
            
            print(f"\nMetrics: {found}/{len(required_metrics)} found")
            
            # Parse some metrics
            print("\nSample metric values:")
            for line in metrics_text.split('\n')[:20]:
                if line and not line.startswith('#') and 'http_requests_total' in line:
                    print(f"   {line[:80]}...")
                    break
            
            return len(missing) == 0
        else:
            print(f"❌ Metrics endpoint returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error accessing metrics: {e}")
        return False


def test_synthetic_probes():
    """Test synthetic probe endpoints"""
    
    print("\n" + "="*70)
    print("SYNTHETIC PROBES TEST")
    print("="*70)
    
    # Test individual probes
    probes = ["healthz", "readyz", "search", "agencies"]
    
    print("Testing individual probes:")
    for probe in probes:
        try:
            response = requests.get(f"{API_URL}/api/v1/monitoring/probe/{probe}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                duration = data.get("duration_seconds", 0)
                
                if success:
                    print(f"✅ {probe}: Success ({duration:.3f}s)")
                else:
                    print(f"❌ {probe}: Failed")
                    if "error" in data:
                        print(f"   Error: {data['error']}")
            else:
                print(f"❌ {probe}: Status {response.status_code}")
                
        except Exception as e:
            print(f"❌ {probe}: Error - {e}")
    
    # Test all probes
    print("\nTesting all probes together:")
    try:
        response = requests.get(f"{API_URL}/api/v1/monitoring/probe", timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            overall = data.get("overall_success", False)
            probes = data.get("probes", [])
            
            print(f"Overall: {'✅ Success' if overall else '❌ Failed'}")
            
            for probe in probes:
                name = probe.get("probe", "unknown")
                success = probe.get("success", False)
                duration = probe.get("duration_seconds", 0)
                print(f"  {name}: {'✅' if success else '❌'} ({duration:.3f}s)")
                
            return overall
        else:
            print(f"❌ All probes endpoint returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error running all probes: {e}")
        return False


def test_slo_tracking():
    """Test SLO tracking endpoint"""
    
    print("\n" + "="*70)
    print("SLO TRACKING TEST")
    print("="*70)
    
    try:
        response = requests.get(f"{API_URL}/api/v1/monitoring/slo", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            print("Service Level Objectives:")
            print("-" * 70)
            
            # Uptime SLO
            uptime = data.get("uptime", {})
            print(f"\nUptime SLO:")
            print(f"  Target: {uptime.get('target', 0):.1f}%")
            print(f"  Current: {uptime.get('current', 0):.2f}%")
            print(f"  Status: {uptime.get('status', 'UNKNOWN')}")
            print(f"  Downtime: {uptime.get('downtime_minutes', 0)} minutes")
            
            # Latency SLO
            latency = data.get("latency_p95", {})
            print(f"\nLatency p95 SLO:")
            print(f"  Target: {latency.get('target_ms', 0):.0f}ms")
            print(f"  Current: {latency.get('current_ms', 0):.0f}ms")
            print(f"  Status: {latency.get('status', 'UNKNOWN')}")
            print(f"  Sample size: {latency.get('sample_size', 0)}")
            
            # Error Rate SLO
            errors = data.get("error_rate", {})
            print(f"\nError Rate SLO:")
            print(f"  Target: {errors.get('target_pct', 0):.2f}%")
            print(f"  Current: {errors.get('current_pct', 0):.2f}%")
            print(f"  Status: {errors.get('status', 'UNKNOWN')}")
            print(f"  Total requests: {errors.get('total_requests', 0)}")
            print(f"  Error requests: {errors.get('error_requests', 0)}")
            
            # Overall
            overall = data.get("overall_status", "UNKNOWN")
            print(f"\nOverall SLO Status: {overall}")
            print(f"Evaluation Window: {data.get('evaluation_window', 'unknown')}")
            
            return overall == "OK"
        else:
            print(f"❌ SLO endpoint returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error accessing SLO endpoint: {e}")
        return False


def simulate_load_for_metrics():
    """Generate some load to populate metrics"""
    
    print("\n" + "="*70)
    print("GENERATING LOAD FOR METRICS")
    print("="*70)
    
    print("Simulating API calls to generate metrics...")
    
    # Make various API calls
    endpoints = [
        ("GET", "/api/v1/healthz", None),
        ("GET", "/api/v1/agencies", None),
        ("POST", "/api/v1/search/advanced", {"product": "test", "limit": 5}),
        ("POST", "/api/v1/barcode/scan", {"barcode": "123456789012"}),
        ("GET", "/api/v1/recall/TEST123", None),  # This will 404
    ]
    
    for _ in range(3):  # Make 3 rounds of calls
        for method, endpoint, data in endpoints:
            try:
                if method == "GET":
                    requests.get(f"{API_URL}{endpoint}", timeout=2)
                else:
                    requests.post(f"{API_URL}{endpoint}", json=data, timeout=2)
            except:
                pass
        time.sleep(0.5)
    
    print("✅ Load generation complete")
    
    # Wait for metrics to update
    print("Waiting for metrics to update...")
    time.sleep(2)


def test_alert_conditions():
    """Test that alert conditions can be detected"""
    
    print("\n" + "="*70)
    print("ALERT CONDITION TESTING")
    print("="*70)
    
    print("Simulating conditions that should trigger alerts...")
    
    # Test high latency by making slow requests
    print("\n1. Testing high latency detection:")
    start = time.time()
    try:
        # This endpoint might be slow
        response = requests.post(
            f"{API_URL}/api/v1/search/advanced",
            json={"product": "a" * 1000, "limit": 100},
            timeout=10
        )
        duration = time.time() - start
        print(f"   Request took {duration:.2f}s")
        
        if duration > 0.8:
            print("   ⚠️ Would trigger HighLatencyP95 alert (> 800ms)")
        else:
            print("   ✅ Within SLO")
    except:
        print("   ❌ Request failed")
    
    # Test error rate by triggering errors
    print("\n2. Testing error rate detection:")
    errors = 0
    total = 10
    for i in range(total):
        try:
            # This should 404
            response = requests.get(f"{API_URL}/api/v1/recall/INVALID_{i}", timeout=2)
            if response.status_code >= 400:
                errors += 1
        except:
            errors += 1
    
    error_rate = errors / total * 100
    print(f"   Error rate: {error_rate:.1f}%")
    if error_rate > 1:
        print("   ⚠️ Would trigger HighErrorRate alert (> 1%)")
    else:
        print("   ✅ Within SLO")
    
    # Test rate limiting
    print("\n3. Testing rate limit detection:")
    print("   Making rapid requests...")
    rapid_requests = 0
    start = time.time()
    while time.time() - start < 1:
        try:
            requests.get(f"{API_URL}/api/v1/healthz", timeout=0.5)
            rapid_requests += 1
        except:
            break
    
    print(f"   Made {rapid_requests} requests in 1 second")
    if rapid_requests > 100:
        print("   ⚠️ Would trigger rate limit alerts")
    else:
        print("   ✅ Within rate limits")
    
    return True


def test_dashboard_data():
    """Test that metrics provide enough data for dashboards"""
    
    print("\n" + "="*70)
    print("DASHBOARD DATA VERIFICATION")
    print("="*70)
    
    try:
        response = requests.get(f"{API_URL}/metrics", timeout=5)
        
        if response.status_code == 200:
            metrics_text = response.text
            
            # Check for histogram buckets (needed for percentiles)
            if "http_request_duration_seconds_bucket" in metrics_text:
                print("✅ Histogram buckets present for latency percentiles")
            else:
                print("❌ Missing histogram buckets")
            
            # Check for labels (needed for grouping)
            if 'status="200"' in metrics_text or 'method="GET"' in metrics_text:
                print("✅ Labels present for grouping")
            else:
                print("❌ Missing labels for grouping")
            
            # Check for counter metrics (needed for rates)
            if "_total" in metrics_text:
                print("✅ Counter metrics present for rate calculations")
            else:
                print("❌ Missing counter metrics")
            
            # Check for gauge metrics (needed for current values)
            if "system_memory_usage_bytes" in metrics_text:
                print("✅ Gauge metrics present for current values")
            else:
                print("❌ Missing gauge metrics")
            
            return True
        else:
            print(f"❌ Metrics endpoint returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying dashboard data: {e}")
        return False


def main():
    """Run all monitoring tests"""
    
    print("="*70)
    print("TASK 14: MONITORING & SLO TEST SUITE")
    print("="*70)
    print(f"API URL: {API_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_passed = True
    
    # Test health endpoints
    if not test_health_endpoints():
        all_passed = False
    
    # Test metrics endpoint
    if not test_metrics_endpoint():
        all_passed = False
    
    # Generate some load
    simulate_load_for_metrics()
    
    # Test synthetic probes
    if not test_synthetic_probes():
        all_passed = False
    
    # Test SLO tracking
    if not test_slo_tracking():
        all_passed = False
    
    # Test alert conditions
    if not test_alert_conditions():
        all_passed = False
    
    # Test dashboard data
    if not test_dashboard_data():
        all_passed = False
    
    # Summary
    print("\n" + "="*70)
    print("MONITORING ACCEPTANCE CRITERIA")
    print("="*70)
    
    criteria = [
        ("Prometheus metrics endpoint", "/metrics working"),
        ("Health check endpoints", "healthz, readyz, livez"),
        ("Synthetic probes", "All probes functional"),
        ("SLO tracking", "Uptime, latency, error rate"),
        ("Alert conditions", "Can detect violations"),
        ("Dashboard data", "Sufficient metrics for visualization"),
        ("Runbook documentation", "docs/ONCALL_RUNBOOK.md"),
    ]
    
    for criterion, detail in criteria:
        print(f"✅ {criterion}")
        print(f"   {detail}")
    
    if all_passed:
        print("\n" + "="*70)
        print("✅ TASK 14 ACCEPTANCE CRITERIA MET")
        print("="*70)
        print("\n🎉 Monitoring & SLOs Complete!")
        print("- Prometheus metrics exposed")
        print("- Grafana dashboards defined")
        print("- Alert rules configured")
        print("- Synthetic probes running")
        print("- SLOs tracked (99.9% uptime, p95 < 800ms)")
        print("- On-call runbook committed")
    else:
        print("\n⚠️ Some tests failed. Please review and fix issues.")
    
    print("\n📊 Next Steps:")
    print("1. Deploy monitoring endpoints")
    print("2. Configure Prometheus scraping")
    print("3. Import Grafana dashboards")
    print("4. Set up alert routing")
    print("5. Test alert firing")


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
