"""Fix function 6 (fix_upc_data) by replacing RecallDB dead code"""


def fix_function6():
    file_path = "api/main_crownsafe.py"

    # Read the file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the function start and end
    start_marker = "# REMOVED FOR CROWN SAFE: RecallDB model no longer exists (replaced with HairProductModel)\n        # from core_infra.database import RecallDB\n\n        with get_db_session() as db:"  # noqa: E501
    end_marker = 'logger.info(f"Ã°Å¸Å½â€° UPC Enhancement Complete: {upc_coverage}% coverage achieved!")\n\n            return result'  # noqa: E501

    # New code to insert
    new_code = """# REMOVED FOR CROWN SAFE: RecallDB model no longer exists (replaced with HairProductModel)
        # from core_infra.database import RecallDB
        
        # REMOVED FOR CROWN SAFE: Baby product recall UPC enhancement replaced
        # This function previously enhanced baby product recalls with UPC barcodes
        # TODO: Implement Crown Safe hair product barcode system using HairProductModel
        logger.info("UPC data enhancement endpoint called (Crown Safe barcode system not yet implemented)")

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

        return result"""

    # Find positions
    start_pos = content.find(start_marker)
    if start_pos == -1:
        print("ERROR: Could not find start marker")
        return False

    end_search_start = start_pos + len(start_marker)
    end_pos = content.find(end_marker, end_search_start)
    if end_pos == -1:
        print("ERROR: Could not find end marker")
        return False

    # Include the end marker
    end_pos += len(end_marker)

    # Replace
    new_content = content[:start_pos] + new_code + content[end_pos:]

    # Write back
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✓ Successfully replaced {end_pos - start_pos} characters with {len(new_code)} characters")
    print(f"✓ Net reduction: {(end_pos - start_pos) - len(new_code)} characters")
    return True


if __name__ == "__main__":
    success = fix_function6()
    exit(0 if success else 1)
