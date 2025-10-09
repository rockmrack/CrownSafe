import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agents.premium.allergy_sensitivity_agent.agent_logic import (
    AllergySensitivityAgentLogic,
)
from core_infra.database import (
    get_db_session,
    create_tables,
    User,
    Family,
    FamilyMember,
)
from core_infra.auth.auth_manager import create_user

logging.basicConfig(level=logging.INFO)

TEST_EMAIL = "allergy-test-user@babyshield.com"


def setup_test_family():
    """Creates a mock user, family, and members in the database for testing."""
    with get_db_session() as db:
        # Clean up previous runs
        user = db.query(User).filter(User.email == TEST_EMAIL).first()
        if user:
            if user.families:
                for member in user.families[0].members:
                    db.delete(member)
                db.delete(user.families[0])
            db.delete(user)
        db.commit()

        # Create new user and family
        test_user = create_user(db, email=TEST_EMAIL, password="password")
        test_family = Family(family_name="Test Family")
        test_family.users.append(test_user)

        # Create family members with allergies
        liam = FamilyMember(name="Liam", allergies=["peanut traces", "soy lecithin"])
        mom = FamilyMember(name="Mom", allergies=["almond oil"])
        baby = FamilyMember(name="Baby", allergies=["milk"])

        test_family.members.extend([liam, mom, baby])

        db.add(test_family)
        db.commit()
        return test_user.id


def test_allergy_logic():
    print("--- Testing AllergySensitivityAgent Logic ---")
    create_tables()
    user_id = setup_test_family()

    logic = AllergySensitivityAgentLogic(agent_id="test_allergy_agent_01")

    print("\n1. Testing a product with multiple allergens...")
    # This product has peanut traces and soy lecithin
    result = logic.check_product_for_family(user_id, "038000222015")
    assert result["status"] == "success"
    assert result["is_safe"] is False
    assert len(result["alerts"]) == 1
    assert result["alerts"][0]["member_name"] == "Liam"
    assert "peanut traces" in result["alerts"][0]["found_allergens"]
    print("   -> SUCCESS: Correctly identified high risk for Liam.")

    print("\n2. Testing a product with a different allergen...")
    # This product has almond oil
    result = logic.check_product_for_family(user_id, "724120000133")
    assert result["status"] == "success"
    assert result["is_safe"] is False
    assert len(result["alerts"]) == 1
    assert result["alerts"][0]["member_name"] == "Mom"
    print("   -> SUCCESS: Correctly identified high risk for Mom.")

    print("\n3. Testing a product that is safe for everyone...")
    # This product only has milk, which is not a listed allergy for the baby in this test
    result = logic.check_product_for_family(user_id, "8801043158451")
    assert result["status"] == "success"
    assert result["is_safe"] is True
    assert len(result["alerts"]) == 0
    print("   -> SUCCESS: Correctly identified the product as safe for the family.")

    print("\n--- All tests passed successfully! AllergySensitivityAgent is working. ---")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    test_allergy_logic()
