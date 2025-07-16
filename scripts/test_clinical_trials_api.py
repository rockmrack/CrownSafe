# C:\Users\rossd\Downloads\RossNetAgents\scripts\test_clinical_trials_api.py
# Purpose: Direct test of ClinicalTrials.gov API v2
# From: Claude's suggestion (Option 1) - MODIFIED to remove problematic Unicode characters for Windows console

import requests
import json
import os # For environment variable if needed for future proxy settings

def test_clinical_trials_api():
    """Test the ClinicalTrials.gov API v2 with different parameter combinations"""
    
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    
    # Test cases
    test_cases = [
        {
            "name": "Drug only (Metformin) - query.intr",
            "params": {
                "query.intr": "Metformin",
                "pageSize": "3",
                "format": "json"
            }
        },
        {
            "name": "Condition only (Type 2 Diabetes) - query.cond", 
            "params": {
                "query.cond": "Type 2 Diabetes",
                "pageSize": "3",
                "format": "json"
            }
        },
        {
            "name": "Drug + Condition - query.intr AND query.cond",
            "params": {
                "query.intr": "Metformin",
                "query.cond": "Type 2 Diabetes", 
                "pageSize": "3",
                "format": "json"
            }
        },
        {
            "name": "General term - query.term (Metformin diabetes)",
            "params": {
                "query.term": "Metformin diabetes",
                "pageSize": "3", 
                "format": "json"
            }
        },
        {
            "name": "General term - query.term (Metformin AND \"Type 2 Diabetes\")", # Simulates one possible agent query
            "params": {
                "query.term": "Metformin AND \"Type 2 Diabetes\"",
                "pageSize": "3",
                "format": "json"
            }
        },
        {
            "name": "General term - expr (Metformin AND \"Type 2 Diabetes\")", # Simulates agent's current query construction
            "params": {
                "expr": "Metformin AND \"Type 2 Diabetes\"", 
                "pageSize": "3",
                "format": "json"
            }
        }
    ]
    
    # Check for proxy settings - useful for corporate environments
    proxies = {
        "http": os.environ.get('HTTP_PROXY'),
        "https": os.environ.get('HTTPS_PROXY'),
    }
    # Remove None proxies
    proxies = {k: v for k, v in proxies.items() if v}
    if proxies:
        print(f"INFO: Using proxies: {proxies}")

    for test_case in test_cases:
        print(f"\n{'='*50}")
        print(f"Testing: {test_case['name']}")
        print(f"Parameters: {test_case['params']}")
        
        # Construct the request to get the full URL for logging
        prepared_request = requests.Request('GET', base_url, params=test_case['params']).prepare()
        print(f"Full URL: {prepared_request.url}")
        print(f"{'='*50}")
        
        try:
            response = requests.get(base_url, params=test_case['params'], timeout=30, proxies=proxies if proxies else None)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                total_count = data.get('totalCount', 0)
                studies = data.get('studies', [])
                
                print(f"SUCCESS!") # Changed from emoji
                print(f"Total studies found: {total_count}")
                print(f"Studies returned: {len(studies)}")
                
                if studies:
                    first_study = studies[0]
                    protocol_section = first_study.get('protocolSection', {})
                    identification_module = protocol_section.get('identificationModule', {})
                    status_module = protocol_section.get('statusModule', {})
                    conditions_module = protocol_section.get('conditionsModule', {})
                    interventions_module = protocol_section.get('interventionsModule', {})
                    
                    print(f"  First study NCT ID: {identification_module.get('nctId', 'N/A')}")
                    print(f"  Brief Title: {identification_module.get('briefTitle', 'N/A')[:100]}...")
                    print(f"  Overall Status: {status_module.get('overallStatus', 'N/A')}")
                    print(f"  Conditions: {conditions_module.get('conditions', [])}")
                    # Check if interventionList and intervention exist before list comprehension
                    intervention_list = interventions_module.get('interventionList', {})
                    interventions = intervention_list.get('intervention', []) if intervention_list else []
                    if interventions:
                        print(f"  Interventions: {[i.get('name') for i in interventions if isinstance(i, dict)]}")
                    else:
                        print(f"  Interventions: N/A or empty list")
                    
            else:
                print(f"FAILED!") # Changed from emoji
                print(f"Response Text (first 500 chars): {response.text[:500]}...")
                
        except requests.exceptions.Timeout:
            print(f"ERROR: Request timed out after 30 seconds.") # Changed from emoji
        except requests.exceptions.ConnectionError as ce:
            print(f"ERROR: Connection Error: {ce}") # Changed from emoji
        except Exception as e:
            print(f"ERROR: An unexpected error occurred: {e}") # Changed from emoji

if __name__ == "__main__":
    print("Testing ClinicalTrials.gov API v2 (Directly - No Emojis)...")
    test_clinical_trials_api()
    print("\nTest completed!")