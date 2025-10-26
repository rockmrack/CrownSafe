# Manual Fix Required: Function 6 (fix_upc_data)

## Status
❌ **BLOCKED**: File encoding/descriptor errors prevent automated replacement  
⚠️ **ACTION REQUIRED**: Manual VS Code edit needed

## Location
**File**: `api/main_babyshield.py`  
**Lines**: 3839-3933 (approximately 95 lines)  
**Function**: `fix_upc_data()`

## Current Code to Replace
Starting at line 3848, find this block:

```python
        # REMOVED FOR CROWN SAFE: RecallDB model no longer exists (replaced with HairProductModel)
        # from core_infra.database import RecallDB

        with get_db_session() as db:
            # Get recalls without UPC codes
            recalls_without_upc = (
                db.query(RecallDB).filter(RecallDB.upc.is_(None)).limit(200).all()
            )  # Process in batches

            logger.info(f"Found {len(recalls_without_upc)} recalls without UPC codes")

            enhanced_count = 0

            # Enhanced UPC mapping for common baby products
            upc_mappings = {
                # Baby food and formula
                "gerber": "015000073114",
                "enfamil": "300871214415",
                "similac": "070074575842",
                "earth's best": "023923330016",
                # Baby gear
                "fisher-price": "041220787346",
                "graco": "047406130139",
                "chicco": "049796007434",
                "evenflo": "032884322502",
                # Common baby products
                "johnson": "381370036746",
                "pampers": "037000863441",
                "huggies": "036000406719",
                "baby food": "015000073114",
                "baby formula": "300871214415",
                "car seat": "041220787346",
                "stroller": "047406130139",
                "high chair": "049796007434",
                "baby monitor": "032884322502",
            }

            for recall in recalls_without_upc:
                try:
                    if recall.product_name:
                        product_lower = recall.product_name.lower()

                        # Find matching UPC based on product name keywords
                        for keyword, upc in upc_mappings.items():
                            if keyword in product_lower:
                                # Add some variation to avoid all same UPC
                                base_upc = upc[:-1]  # Remove last digit
                                variant = str(enhanced_count % 10)  # Add variant digit
                                enhanced_upc = base_upc + variant

                                recall.upc = enhanced_upc
                                enhanced_count += 1
                                logger.info(f"✓ Enhanced '{recall.product_name[:40]}...' with UPC {enhanced_upc}")
                                break

                except Exception as e:
                    logger.warning(f"Failed to enhance recall {recall.recall_id}: {e}")

            # Commit changes
            if enhanced_count > 0:
                db.commit()
                logger.info(f"Ã°Å¸Å½Â¯ Successfully enhanced {enhanced_count} recalls with UPC data")

            # Get final statistics
            final_upc_count = db.query(RecallDB).filter(RecallDB.upc.isnot(None)).count()
            total_recalls = db.query(RecallDB).count()
            upc_coverage = round((final_upc_count / total_recalls) * 100, 2) if total_recalls > 0 else 0

            result = {
                "status": "completed",
                "enhanced_recalls": enhanced_count,
                "total_with_upc": final_upc_count,
                "total_recalls": total_recalls,
                "upc_coverage_percent": upc_coverage,
                "agencies_optimized": 39,
                "impact": "Barcode scanning now functional!",
            }

            logger.info(f"Ã°Å¸Å½â€° UPC Enhancement Complete: {upc_coverage}% coverage achieved!")

            return result
```

## Replacement Code
Replace the entire block above with:

```python
        # REMOVED FOR CROWN SAFE: RecallDB model no longer exists (replaced with HairProductModel)
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

        return result
```

## Manual Steps (VS Code)

### Step 1: Open File
1. Open `api/main_babyshield.py` in VS Code
2. Press `Ctrl+G` and type `3848` to jump to line 3848

### Step 2: Select Dead Code Block
1. Position cursor at line 3848 (should see the comment `# REMOVED FOR CROWN SAFE`)
2. Hold `Shift` and press `Ctrl+G`, type `3928` to select lines 3848-3928
3. OR manually select from line 3848 to line 3928 (ending at `return result`)

### Step 3: Replace with New Code
1. Delete the selected text (`Ctrl+X` or `Delete`)
2. Paste the replacement code from above

### Step 4: Verify
1. Save file (`Ctrl+S`)
2. Check that:
   - No more `RecallDB` references remain in function
   - Function returns empty result dictionary
   - TODO comment is present for future Crown Safe implementation

## Expected Outcome
- **Lint Errors**: Should drop to ~31 errors (from ~33)
- **RecallDB Errors**: Zero remaining (currently 3 at lines 3854, 3911, 3912)
- **File Size**: ~3,947 lines (down from current ~4,032)
- **Net Reduction**: ~85 lines removed from function 6
- **Total Dead Code Removed**: ~349 lines across all 6 functions

## Verification Commands
After manual edit, run:
```bash
# Check for remaining RecallDB references
python -m api.main_babyshield  # Should start without NameError

# Or grep for any remaining issues
grep -n "RecallDB" api/main_babyshield.py  # Should only show commented imports
```

## Impact
Once complete, this will be the **final step** to eliminate all RecallDB dead code, allowing the server to start without `NameError` crashes.

---
**Created**: $(Get-Date)  
**Priority**: 🔴 CRITICAL - Blocks server startup  
**Estimated Time**: 3 minutes  
**Difficulty**: Easy (copy/paste replacement)
