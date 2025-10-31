import os
from unittest.mock import patch

import pytest

from api.services.alternatives_provider import get_alternatives


class TestAlternativesProvider:
    """Tests for alternatives provider rules engine."""

    def test_cheese_alternatives(self) -> None:
        scan_data = {
            "category": "cheese",
            "flags": ["soft_cheese"],
            "ingredients": ["milk", "cultures"],
            "profile": {},
        }

        result = get_alternatives(scan_data)

        assert result["schema"] == "AlternativesOut@v1"
        assert len(result["items"]) == 2

        # Check pasteurised brie alternative
        pasteurised_brie = next(item for item in result["items"] if item["id"] == "alt_pasteurised_brie")
        assert pasteurised_brie["name"] == "Pasteurised Brie (labeled)"
        assert pasteurised_brie["pregnancy_safe"] is True
        assert "pasteurised" in pasteurised_brie["tags"]
        assert "pregnancy" in pasteurised_brie["tags"]
        assert len(pasteurised_brie["evidence"]) == 1
        assert pasteurised_brie["evidence"][0]["type"] == "label"

        # Check hard cheese alternative
        hard_cheese = next(item for item in result["items"] if item["id"] == "alt_hard_cheese")
        assert hard_cheese["name"] == "Hard cheeses (Cheddar, Gruyère)"
        assert hard_cheese["pregnancy_safe"] is True
        assert "pregnancy" in hard_cheese["tags"]
        assert len(hard_cheese["evidence"]) == 1
        assert hard_cheese["evidence"][0]["type"] == "regulatory"

    def test_peanut_allergy_alternatives(self) -> None:
        scan_data = {
            "category": "snack",
            "ingredients": ["peanuts", "salt", "oil"],
            "profile": {"allergies": ["peanut"]},
        }

        result = get_alternatives(scan_data)

        assert len(result["items"]) == 2

        # Check nut-free bar
        nut_free_bar = next(item for item in result["items"] if item["id"] == "alt_peanut_free_bar")
        assert nut_free_bar["name"] == "Nut-free snack bar"
        assert "peanut" in nut_free_bar["allergy_safe_for"]
        assert "peanut-free" in nut_free_bar["tags"]

        # Check sunbutter alternative
        sunbutter = next(item for item in result["items"] if item["id"] == "alt_sunbutter")
        assert sunbutter["name"] == "SunButter (sunflower seed spread)"
        assert "peanut" in sunbutter["allergy_safe_for"]
        assert "spread" in sunbutter["tags"]

    def test_tree_nut_allergy_alternatives(self) -> None:
        scan_data = {
            "category": "granola",
            "ingredients": ["oats", "almonds", "honey"],
            "profile": {"allergies": ["almond", "walnut"]},
        }

        result = get_alternatives(scan_data)

        assert len(result["items"]) == 1

        # Check nut-free granola
        nut_free_granola = next(item for item in result["items"] if item["id"] == "alt_nut_free_granola")
        assert nut_free_granola["name"] == "Nut-free granola or oat bars"
        assert "almond" in nut_free_granola["allergy_safe_for"]
        assert "walnut" in nut_free_granola["allergy_safe_for"]
        assert "nut-free" in nut_free_granola["tags"]

    def test_sleep_surface_alternatives(self) -> None:
        scan_data = {
            "category": "infant_sleeper",
            "flags": ["sleep_surface", "inclined"],
            "profile": {},
        }

        result = get_alternatives(scan_data)

        assert len(result["items"]) == 2

        # Check flat sleep surface
        flat_sleep = next(item for item in result["items"] if item["id"] == "alt_flat_sleep_surface")
        assert flat_sleep["name"] == "Flat, firm sleep surface (crib/bassinet with fitted sheet)"
        assert flat_sleep["age_min_months"] == 0
        assert "flat-sleep" in flat_sleep["tags"]
        assert "safe-sleep" in flat_sleep["tags"]

        # Check bassinet
        bassinet = next(item for item in result["items"] if item["id"] == "alt_bassinet")
        assert bassinet["name"] == "CPSC-compliant bassinet"
        assert bassinet["age_min_months"] == 0
        assert "cpsc-approved" in bassinet["tags"]

    def test_small_parts_toy_alternatives(self) -> None:
        scan_data = {
            "category": "toy",
            "flags": ["small_parts", "choking_hazard"],
            "profile": {},
        }

        result = get_alternatives(scan_data)

        assert len(result["items"]) == 2

        # Check large-piece toy
        large_piece = next(item for item in result["items"] if item["id"] == "alt_large_piece_toy")
        assert large_piece["name"] == "Large-piece version of similar toy"
        assert large_piece["age_min_months"] == 0
        assert "no-small-parts" in large_piece["tags"]

        # Check soft toy
        soft_toy = next(item for item in result["items"] if item["id"] == "alt_soft_toy")
        assert soft_toy["name"] == "Soft fabric toy without detachable parts"
        assert "soft" in soft_toy["tags"]
        assert "no-small-parts" in soft_toy["tags"]

    def test_cosmetic_pregnancy_alternatives(self) -> None:
        scan_data = {
            "category": "cosmetic",
            "ingredients": ["water", "retinol", "glycerin"],
            "profile": {},
        }

        result = get_alternatives(scan_data)

        assert len(result["items"]) == 1

        # Check pregnancy-safe skincare
        safe_skincare = next(item for item in result["items"] if item["id"] == "alt_pregnancy_safe_skincare")
        assert safe_skincare["name"] == "Pregnancy-safe skincare (vitamin C, hyaluronic acid)"
        assert safe_skincare["pregnancy_safe"] is True
        assert "pregnancy-safe" in safe_skincare["tags"]
        assert "skincare" in safe_skincare["tags"]

    def test_high_mercury_fish_alternatives(self) -> None:
        scan_data = {"category": "fish", "flags": ["high_mercury"], "profile": {}}

        result = get_alternatives(scan_data)

        assert len(result["items"]) == 1

        # Check low-mercury fish
        low_mercury = next(item for item in result["items"] if item["id"] == "alt_low_mercury_fish")
        assert low_mercury["name"] == "Low-mercury fish (salmon, sardines, anchovies)"
        assert low_mercury["pregnancy_safe"] is True
        assert "low-mercury" in low_mercury["tags"]
        assert "omega-3" in low_mercury["tags"]

    def test_raw_dairy_alternatives(self) -> None:
        scan_data = {
            "category": "dairy",
            "ingredients": ["raw milk", "cultures"],
            "profile": {},
        }

        result = get_alternatives(scan_data)

        assert len(result["items"]) == 1

        # Check pasteurized dairy
        pasteurized = next(item for item in result["items"] if item["id"] == "alt_pasteurized_dairy")
        assert pasteurized["name"] == "Pasteurized version of same product"
        assert pasteurized["pregnancy_safe"] is True
        assert "pasteurized" in pasteurized["tags"]

    def test_no_alternatives_when_no_rules_match(self) -> None:
        scan_data = {
            "category": "general",
            "ingredients": ["water", "salt"],
            "profile": {},
        }

        result = get_alternatives(scan_data)

        assert result["schema"] == "AlternativesOut@v1"
        assert len(result["items"]) == 0

    def test_max_three_alternatives_limit(self) -> None:
        # Create a scan that would trigger multiple rules
        scan_data = {
            "category": "cheese",  # triggers cheese rules (2 items)
            "flags": [
                "soft_cheese",
                "small_parts",
            ],  # triggers toy rules (2 more items)
            "ingredients": [
                "peanuts",
                "raw milk",
            ],  # triggers peanut + dairy rules (3 more items)
            "profile": {"allergies": ["peanut", "tree_nut"]},  # triggers more allergy rules
        }

        result = get_alternatives(scan_data)

        # Should be limited to 3 items max
        assert len(result["items"]) <= 3

    def test_feature_flag_disabled(self) -> None:
        with patch.dict(os.environ, {"BS_ALTERNATIVES_ENABLED": "false"}):
            scan_data = {"category": "cheese", "flags": ["soft_cheese"], "profile": {}}

            result = get_alternatives(scan_data)

            assert result["schema"] == "AlternativesOut@v1"
            assert len(result["items"]) == 0

    def test_feature_flag_enabled_by_default(self) -> None:
        # Ensure feature is enabled by default
        with patch.dict(os.environ, {}, clear=True):
            scan_data = {"category": "cheese", "flags": ["soft_cheese"], "profile": {}}

            result = get_alternatives(scan_data)

            assert len(result["items"]) > 0

    def test_evidence_structure(self) -> None:
        scan_data = {"category": "cheese", "flags": ["soft_cheese"], "profile": {}}

        result = get_alternatives(scan_data)

        # Check evidence structure for pasteurised brie
        pasteurised_brie = next(item for item in result["items"] if item["id"] == "alt_pasteurised_brie")
        evidence = pasteurised_brie["evidence"][0]

        assert evidence["type"] == "label"
        assert evidence["source"] == "Product label"
        assert evidence["id"] == "pasteurisation"
        assert evidence["url"] is None

    def test_complex_allergy_scenario(self) -> None:
        # Test complex scenario with multiple allergens
        scan_data = {
            "category": "snack",
            "ingredients": ["peanuts", "almonds", "soy lecithin"],
            "profile": {"allergies": ["peanut", "tree_nut", "soy"]},
        }

        result = get_alternatives(scan_data)

        # Should get alternatives for both peanut and tree nut allergies
        assert len(result["items"]) >= 2

        # Check that alternatives are safe for the specific allergies
        for item in result["items"]:
            if "peanut" in item["allergy_safe_for"]:
                assert "peanut-free" in item["tags"] or "nut-free" in item["tags"]


if __name__ == "__main__":
    pytest.main([__file__])
