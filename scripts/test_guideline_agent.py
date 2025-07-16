import asyncio
import logging
import json
from pathlib import Path
import sys
import os

# Add project root to path - handle both development and deployed scenarios
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent

# Add both the project root and the current directory to path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_file.parent))

# Now try to import - with better error handling
try:
    from agents.guideline_agent.agent_logic import GuidelineAgentLogic
    print(f"✅ Successfully imported GuidelineAgentLogic from {project_root}")
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path}")
    print("\nDirectory structure:")
    for root, dirs, files in os.walk(project_root / "agents"):
        level = root.replace(str(project_root), '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            if file.endswith('.py'):
                print(f"{subindent}{file}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\n")

def print_result(result: dict, indent: int = 2):
    """Pretty print a result dictionary"""
    indent_str = " " * indent
    for key, value in result.items():
        if isinstance(value, dict):
            print(f"{indent_str}{key}:")
            print_result(value, indent + 2)
        elif isinstance(value, list):
            print(f"{indent_str}{key}: [{len(value)} items]")
            if value and len(value) <= 3:  # Show first few items if list is small
                for item in value:
                    if isinstance(item, dict):
                        print(f"{indent_str}  -")
                        print_result(item, indent + 4)
                    else:
                        print(f"{indent_str}  - {item}")
        else:
            # Truncate long strings
            if isinstance(value, str) and len(value) > 100:
                print(f"{indent_str}{key}: {value[:100]}...")
            else:
                print(f"{indent_str}{key}: {value}")

async def test_guideline_agent():
    """Test the GuidelineAgent functionality"""
    
    print_section("TESTING GUIDELINE AGENT")
    
    # Initialize the agent logic
    agent_id = "test_guideline_agent_01"
    
    try:
        logic = GuidelineAgentLogic(agent_id=agent_id)
        print(f"✅ Successfully initialized GuidelineAgentLogic")
    except Exception as e:
        print(f"❌ Failed to initialize GuidelineAgentLogic: {e}")
        return
    
    # Test 1: Ingest AHA Heart Failure Guideline
    print_section("Test 1: Guideline Ingestion")
    
    ingestion_task = {
        "task_name": "ingest_guideline",
        "guideline_id": "AHA_HF_2022",
        "task_id": "test_task_001",
        "workflow_id": "test_workflow_001"
    }
    
    print("Ingesting AHA Heart Failure 2022 Guideline...")
    print(f"Task data: {json.dumps(ingestion_task, indent=2)}")
    
    try:
        result = logic.process_task(ingestion_task)
        print("\nIngestion Result:")
        print_result(result)
        
        if result['status'] != 'COMPLETED':
            print("\n❌ INGESTION FAILED!")
            return
        else:
            print(f"\n✅ Successfully ingested {result.get('chunks_count', 0)} chunks")
    except Exception as e:
        print(f"\n❌ Error during ingestion: {e}")
        logger.error("Ingestion error", exc_info=True)
        return
    
    # Test 2: Query for SGLT2 inhibitors in heart failure
    print_section("Test 2: Query for SGLT2 Inhibitors")
    
    query_task = {
        "task_name": "query_guidelines",
        "drug_name": "empagliflozin",
        "condition": "heart failure",
        "task_id": "test_task_002",
        "workflow_id": "test_workflow_001"
    }
    
    print("Querying for empagliflozin in heart failure...")
    print(f"Task data: {json.dumps(query_task, indent=2)}")
    
    try:
        result = logic.process_task(query_task)
        print("\nQuery Result:")
        print_result(result)
        
        if result['status'] == 'COMPLETED' and result.get('results'):
            print(f"\n✅ Found {result['total_matches']} relevant sections")
            
            # Show top results
            print("\nTop Matching Sections:")
            for i, match in enumerate(result['results'][:3]):
                print(f"\n--- Match {i+1} (Relevance: {match.get('relevance_score', 0):.2f}) ---")
                print(f"Guideline: {match.get('guideline_name', 'Unknown')}")
                print(f"Text preview: {match['text'][:300]}...")
                
            # Show PA criteria if found
            if result.get('pa_criteria'):
                print("\n--- Extracted PA Criteria ---")
                criteria = result['pa_criteria']
                
                if criteria.get('recommendations'):
                    print("\nRecommendations:")
                    for rec in criteria['recommendations']:
                        print(f"  • {rec['text']}")
                        print(f"    Source: {rec['source']} (relevance: {rec.get('relevance', 0):.2f})")
                
                if criteria.get('prerequisites'):
                    print("\nPrerequisites:")
                    for prereq in criteria['prerequisites']:
                        print(f"  • {prereq['text']}")
                        
                if criteria.get('contraindications'):
                    print("\nContraindications:")
                    for contra in criteria['contraindications']:
                        print(f"  • {contra['text']}")
        else:
            print("\n❌ QUERY FAILED or returned no results!")
    except Exception as e:
        print(f"\n❌ Error during query: {e}")
        logger.error("Query error", exc_info=True)
    
    print_section("TEST SUMMARY")
    print("Basic tests completed. Check results above for any failures.")

async def main():
    """Run all tests"""
    try:
        # Check if we can access the data directory
        data_dir = Path(__file__).parent.parent / "data" / "guidelines"
        if not data_dir.exists():
            print(f"Creating data directory: {data_dir}")
            data_dir.mkdir(parents=True, exist_ok=True)
        
        # Main functionality tests
        await test_guideline_agent()
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        logger.error("Test failed", exc_info=True)

if __name__ == "__main__":
    print("Starting GuidelineAgent tests...")
    print(f"Working directory: {os.getcwd()}")
    print(f"Script location: {__file__}")
    print("Note: First run will download ~5MB PDF, subsequent runs will use cached data")
    print("-" * 60)
    
    asyncio.run(main())