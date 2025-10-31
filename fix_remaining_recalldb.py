"""Fix remaining RecallDB references in main_crownsafe.py."""


def fix_fix_upc_data() -> bool:
    """Replace the fix_upc_data function body."""
    file_path = "api/main_crownsafe.py"

    # Read file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if already fixed
    if "db.query(RecallDB).filter(RecallDB.upc.is_(None))" not in content:
        print("✓ fix_upc_data already fixed!")
        return True

    # Find the function
    func_start = content.find("async def fix_upc_data():")
    if func_start == -1:
        print("ERROR: Could not find fix_upc_data function")
        return False

    # Find try block start (after the logger.info line)
    search_start = content.find('logger.info("', func_start)
    search_start = content.find("\n", search_start) + 1
    try_start = content.find("try:", search_start)

    if try_start == -1:
        print("ERROR: Could not find try block")
        return False

    # Find the except block
    except_start = content.find("except Exception as e:", try_start)
    if except_start == -1:
        print("ERROR: Could not find except block")
        return False

    # Find the end of the function (the return statement in except block)
    return_start = content.find('return {"status": "error"', except_start)
    func_end = content.find("}", return_start) + 1

    if func_end == 0:
        print("ERROR: Could not find function end")
        return False

    print(f"Found function from position {try_start} to {func_end}")

    # Extract old code
    old_code = content[try_start:func_end]
    print(f"Old code length: {len(old_code)} characters")

    # New code
    new_code = """try:
        # REMOVED FOR CROWN SAFE: RecallDB model no longer exists (replaced with HairProductModel)
        # from core_infra.database import RecallDB
        
        # REMOVED FOR CROWN SAFE: Baby product recall UPC enhancement replaced
        # This function previously enhanced baby product recalls with UPC barcodes
        # TODO: Implement Crown Safe hair product barcode system using HairProductModel
        logger.info("UPC data enhancement endpoint called - Crown Safe barcode system not yet implemented")

        # Return empty result until Crown Safe implementation
        result = {
            "status": "completed",
            "enhanced_recalls": 0,
            "total_with_upc": 0,
            "total_recalls": 0,
            "upc_coverage_percent": 0,
            "agencies_optimized": 0,
            "impact": "Crown Safe barcode system coming soon",
            "note": "Baby product recall system replaced with Crown Safe hair products"
        }

        logger.info("Crown Safe barcode system not yet implemented")
        return result

    except Exception as e:
        logger.error(f"UPC data enhancement failed: {e}")
        return {"status": "error", "error": str(e), "agencies": 0}"""

    # Replace
    new_content = content[:try_start] + new_code + content[func_end:]

    # Write back
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✓ Successfully replaced {len(old_code)} chars with {len(new_code)} chars")
    print(f"✓ Net reduction: {len(old_code) - len(new_code)} characters")
    return True


if __name__ == "__main__":
    success = fix_fix_upc_data()
    print("\n" + ("=" * 50))
    if success:
        print("✓ All fixes applied successfully!")
        print("\nNext steps:")
        print("1. Verify no RecallDB references remain: grep -n 'db.query(RecallDB)' api/main_crownsafe.py")
        print("2. Try server startup: python -m uvicorn api.main_crownsafe:app --reload --port 8001")
    else:
        print("✗ Some fixes failed - check errors above")
    exit(0 if success else 1)
