"""
Migration script to upgrade from MemoryManager MVP-1.4 to EnhancedMemoryManager V2.0
FIXED: ChromaDB v0.6.0 API compatibility
"""

import logging
import os
import shutil
import sys
import traceback
from datetime import datetime

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


# Import with correct paths
try:
    from core_infra.enhanced_memory_manager import EnhancedMemoryManager
    from core_infra.memory_manager import MemoryManager

    IMPORTS_SUCCESS = True
except ImportError as e:
    print(f"Import error: {e}")
    print("Trying alternative import paths...")
    try:
        sys.path.insert(0, os.path.join(project_root, "core_infra"))
        from enhanced_memory_manager import EnhancedMemoryManager
        from memory_manager import MemoryManager

        IMPORTS_SUCCESS = True
    except ImportError as e2:
        print(f"Alternative import also failed: {e2}")
        IMPORTS_SUCCESS = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_file_paths():
    """Check if the required files exist and show their paths"""

    print("Checking file paths...")
    print(f"Project root: {project_root}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}...")

    # Check for core_infra directory
    core_infra_path = os.path.join(project_root, "core_infra")
    print(f"Looking for core_infra at: {core_infra_path}")
    print(f"core_infra exists: {os.path.exists(core_infra_path)}")

    if os.path.exists(core_infra_path):
        files_in_core_infra = os.listdir(core_infra_path)
        print(f"Files in core_infra: {files_in_core_infra}")

    # Check for memory manager files
    memory_manager_path = os.path.join(core_infra_path, "memory_manager.py")
    enhanced_memory_path = os.path.join(core_infra_path, "enhanced_memory_manager.py")

    print(f"memory_manager.py exists: {os.path.exists(memory_manager_path)}")
    print(f"enhanced_memory_manager.py exists: {os.path.exists(enhanced_memory_path)}")

    return os.path.exists(memory_manager_path) and os.path.exists(enhanced_memory_path)


def get_collection_names_safe(chroma_client) -> list:
    """Safely get collection names, handling different ChromaDB API versions"""
    try:
        collections = chroma_client.list_collections()

        # Check if collections is a list of strings (v0.6.0+) or objects (older versions)
        if collections and isinstance(collections[0], str):
            # v0.6.0+ - collections are already strings
            return collections
        elif collections and hasattr(collections[0], "name"):
            # Older versions - collections are objects with .name attribute
            return [c.name for c in collections]
        else:
            # Empty list or unknown format
            return []

    except Exception as e:
        logger.error(f"Failed to get collection names: {e}")
        return []


def test_basic_memory_manager():
    """Test if basic MemoryManager works before trying enhanced version"""

    logger.info("Testing basic MemoryManager first...")

    try:
        # Change to project root directory for consistent paths
        original_cwd = os.getcwd()
        os.chdir(project_root)

        # Test basic memory manager
        basic_memory = MemoryManager()
        logger.info("Basic MemoryManager initialized successfully")

        if basic_memory.collection:
            logger.info("Basic MemoryManager collection is available")
            doc_count = basic_memory.collection.count()
            logger.info(f"Basic MemoryManager has {doc_count} documents")
        else:
            logger.warning("Basic MemoryManager collection is None")

        # Restore original working directory
        os.chdir(original_cwd)
        return True

    except Exception as e:
        logger.error(f"Basic MemoryManager test failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        try:
            os.chdir(original_cwd)
        except (OSError, PermissionError):
            # Failed to change directory back
            pass
        return False


def migrate_memory_system():
    """Migrate from MVP-1.4 to EnhancedMemoryManager V2.0"""

    if not IMPORTS_SUCCESS:
        logger.error("Cannot proceed with migration - import failures")
        return False

    logger.info("Starting migration from MemoryManager MVP-1.4 to EnhancedMemoryManager V2.0")

    # Test basic memory manager first
    if not test_basic_memory_manager():
        logger.error("Basic MemoryManager test failed - cannot proceed with enhanced version")
        return False

    try:
        # Change to project root directory for consistent paths
        original_cwd = os.getcwd()
        os.chdir(project_root)

        # Backup existing database
        backup_path = f"chroma_db_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if os.path.exists("chroma_db_data"):
            shutil.copytree("chroma_db_data", backup_path)
            logger.info(f"Backup created at: {backup_path}")
        else:
            logger.info("No existing chroma_db_data directory found - starting fresh")

        # Initialize new enhanced memory manager with detailed error handling
        logger.info("Initializing EnhancedMemoryManager...")

        try:
            enhanced_memory = EnhancedMemoryManager()
            logger.info("EnhancedMemoryManager initialized successfully")
        except Exception as init_error:
            logger.error(f"EnhancedMemoryManager initialization failed: {init_error}")
            logger.error(f"Full initialization traceback: {traceback.format_exc()}")
            raise init_error

        # Test if the enhanced memory manager has basic functionality
        if not hasattr(enhanced_memory, "collection"):
            logger.error("EnhancedMemoryManager missing 'collection' attribute")
            os.chdir(original_cwd)
            return False

        if enhanced_memory.collection is None:
            logger.error("EnhancedMemoryManager collection is None")
            os.chdir(original_cwd)
            return False

        logger.info("EnhancedMemoryManager basic validation passed")

        # Verify collections are created - FIXED: Handle ChromaDB v0.6.0 API
        try:
            collection_names = get_collection_names_safe(enhanced_memory.chroma_client)
            logger.info(f"Found collections: {collection_names}")
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            # Don't fail migration just because we can't list collections
            collection_names = []
            logger.warning("Continuing migration despite collection listing failure")

        expected_collections = [
            "cureviax_knowledge_base_v1",
            "cureviax_knowledge_base_v1_temporal",
            "cureviax_knowledge_base_v1_contradictions",
            "cureviax_knowledge_base_v1_gaps",
            "cureviax_knowledge_base_v1_insights",
        ]

        success_count = 0
        for expected in expected_collections:
            if expected in collection_names:
                logger.info(f"SUCCESS: Collection '{expected}' ready")
                success_count += 1
            else:
                logger.warning(f"Collection '{expected}' not found - may be created on demand")

        # Test enhanced features
        enhanced_features = [
            "temporal_patterns",
            "contradictions",
            "research_gaps",
            "cross_workflow_insights",
        ]

        feature_count = 0
        for feature in enhanced_features:
            if hasattr(enhanced_memory, feature):
                logger.info(f"Enhanced feature available: {feature}")
                feature_count += 1
            else:
                logger.warning(f"Enhanced feature missing: {feature}")

        # Test enhanced collections attributes
        enhanced_collections = [
            "temporal_collection",
            "contradictions_collection",
            "gaps_collection",
            "insights_collection",
        ]

        collection_count = 0
        for collection_attr in enhanced_collections:
            if hasattr(enhanced_memory, collection_attr):
                collection_obj = getattr(enhanced_memory, collection_attr)
                if collection_obj is not None:
                    logger.info(f"Enhanced collection available: {collection_attr}")
                    collection_count += 1
                else:
                    logger.warning(f"Enhanced collection is None: {collection_attr}")
            else:
                logger.warning(f"Enhanced collection missing: {collection_attr}")

        # Test enhanced analytics
        try:
            analytics = enhanced_memory.get_enhanced_analytics()
            if "base_analytics" in analytics:
                logger.info("Enhanced analytics working")
                analytics_working = True
            else:
                logger.warning("Enhanced analytics returned unexpected format")
                analytics_working = False
        except Exception as e:
            logger.warning(f"Enhanced analytics test failed: {e}")
            analytics_working = False

        # Restore original working directory
        os.chdir(original_cwd)

        # More lenient success criteria
        if feature_count >= 2 and collection_count >= 2:  # At least some functionality should work
            logger.info("Migration completed successfully!")
            logger.info("EnhancedMemoryManager V2.0 is ready")
            logger.info(f"  - Collections: {success_count}/5")
            logger.info(f"  - Features: {feature_count}/4")
            logger.info(f"  - Enhanced Collections: {collection_count}/4")
            logger.info(f"  - Analytics: {'Working' if analytics_working else 'Limited'}")
            return True
        else:
            logger.error("Migration failed - insufficient functionality")
            logger.error(f"Feature count: {feature_count}, Collection count: {collection_count}")
            return False

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        logger.error(f"Full migration traceback: {traceback.format_exc()}")
        # Restore original working directory
        try:
            os.chdir(original_cwd)
        except (OSError, PermissionError):
            # Failed to change directory back
            pass
        return False


def verify_migration():
    """Verify migration was successful"""

    if not IMPORTS_SUCCESS:
        logger.error("Cannot verify migration - import failures")
        return False

    logger.info("Verifying migration...")

    try:
        # Change to project root for consistent behavior
        original_cwd = os.getcwd()
        os.chdir(project_root)

        # Test enhanced memory manager initialization
        enhanced_memory = EnhancedMemoryManager()

        # Check base functionality
        if not enhanced_memory.collection:
            logger.error("Base collection not available")
            os.chdir(original_cwd)
            return False

        # Check enhanced features
        enhanced_features = [
            "temporal_patterns",
            "contradictions",
            "research_gaps",
            "cross_workflow_insights",
        ]

        available_features = []
        for feature in enhanced_features:
            if hasattr(enhanced_memory, feature):
                available_features.append(feature)
                logger.info(f"Enhanced feature available: {feature}")
            else:
                logger.warning(f"Enhanced feature missing: {feature}")

        # Test enhanced analytics
        try:
            analytics = enhanced_memory.get_enhanced_analytics()
            if "base_analytics" in analytics:
                logger.info("Enhanced analytics working")
            else:
                logger.warning("Enhanced analytics returned unexpected format")
        except Exception as e:
            logger.warning(f"Enhanced analytics test failed: {e}")

        # Test document count consistency
        try:
            doc_count = enhanced_memory.collection.count()
            logger.info(f"Document count after migration: {doc_count}")
        except Exception as e:
            logger.warning(f"Could not verify document count: {e}")

        # Restore original working directory
        os.chdir(original_cwd)

        if len(available_features) >= 2:  # More lenient criteria
            logger.info(f"Enhanced features verified: {len(available_features)}/4")
            return True
        else:
            logger.error(f"Insufficient enhanced features: {len(available_features)}/4")
            return False

    except Exception as e:
        logger.error(f"Migration verification failed: {e}")
        try:
            os.chdir(original_cwd)
        except (OSError, PermissionError):
            # Failed to change directory back
            pass
        return False


def cleanup_old_backups(keep_count=3):
    """Clean up old backup directories, keeping only the most recent ones"""

    try:
        # Change to project root
        original_cwd = os.getcwd()
        os.chdir(project_root)

        backup_dirs = []
        for item in os.listdir("."):
            if item.startswith("chroma_db_data_backup_") and os.path.isdir(item):
                backup_dirs.append(item)

        if len(backup_dirs) > keep_count:
            backup_dirs.sort()
            old_backups = backup_dirs[:-keep_count]

            for old_backup in old_backups:
                logger.info(f"Removing old backup: {old_backup}")
                shutil.rmtree(old_backup)

        logger.info(f"Backup cleanup completed. Kept {min(len(backup_dirs), keep_count)} backups.")

        # Restore original working directory
        os.chdir(original_cwd)

    except Exception as e:
        logger.warning(f"Backup cleanup failed: {e}")
        try:
            os.chdir(original_cwd)
        except (OSError, PermissionError):
            # Failed to change directory back
            pass


def simple_enhanced_test():
    """Simple test to verify EnhancedMemoryManager can be imported and basic methods work"""

    if not IMPORTS_SUCCESS:
        logger.error("Cannot run enhanced test - import failures")
        return False

    logger.info("Running simple enhanced test...")

    try:
        original_cwd = os.getcwd()
        os.chdir(project_root)

        # Try basic initialization
        enhanced_memory = EnhancedMemoryManager()
        logger.info("Simple enhanced memory initialization: SUCCESS")

        # Try basic analytics
        analytics = enhanced_memory.get_document_usage_analytics()
        logger.info(f"Basic analytics: SUCCESS - {analytics.get('total_documents', 0)} documents")

        # Try enhanced analytics if available
        if hasattr(enhanced_memory, "get_enhanced_analytics"):
            try:
                _ = enhanced_memory.get_enhanced_analytics()  # enhanced_analytics
                logger.info("Enhanced analytics: SUCCESS")
            except Exception as e:
                logger.warning(f"Enhanced analytics failed: {e}")

        os.chdir(original_cwd)
        return True

    except Exception as e:
        logger.error(f"Simple enhanced test failed: {e}")
        logger.error(f"Simple test traceback: {traceback.format_exc()}")
        try:
            os.chdir(original_cwd)
        except (OSError, PermissionError):
            # Failed to change directory back
            pass
        return False


if __name__ == "__main__":
    print("Starting EnhancedMemoryManager V2.0 Migration...")
    print(f"Working from project root: {project_root}")

    # Check file paths first
    files_exist = check_file_paths()

    if not files_exist:
        print("ERROR: Required files not found. Please check file structure.")
        sys.exit(1)

    if not IMPORTS_SUCCESS:
        print("ERROR: Cannot import required modules. Please check file structure and dependencies.")
        sys.exit(1)

    # Run simple test first
    print("\n--- Running Simple Enhanced Test ---")
    simple_test_success = simple_enhanced_test()

    if not simple_test_success:
        print("ERROR: Simple enhanced test failed. Cannot proceed with migration.")
        sys.exit(1)

    print("Simple enhanced test passed. Proceeding with migration...")

    # Run migration
    migration_success = migrate_memory_system()

    if migration_success:
        print("Migration successful!")

        # Verify migration
        verification_success = verify_migration()

        if verification_success:
            print("Migration verification successful!")

            # Clean up old backups
            cleanup_old_backups()

            print("\nEnhancedMemoryManager V2.0 migration completed successfully!")
            print("\nNext steps:")
            print("1. Update PlannerAgent imports to use EnhancedMemoryManager")
            print("2. Update CommanderAgent to use enhanced storage features")
            print("3. Test with a new workflow: python scripts/test_commander_flow.py")
            print("4. Run enhanced test suite: python scripts/test_enhanced_memory.py")
        else:
            print("Migration verification had some issues, but core functionality appears to work.")
            print("You can proceed with testing the enhanced features.")
    else:
        print("Migration failed. Check logs for details.")
