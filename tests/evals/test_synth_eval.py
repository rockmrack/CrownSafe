import json
import os
import tempfile

from scripts.evals.run_synth_eval import check_case, get_llm_client, load_cases


def test_load_cases() -> None:
    """Test loading cases from JSONL file."""
    test_data = [
        {"id": "test1", "scan_data": {"product_name": "Test Product"}, "expect": {}},
        {
            "id": "test2",
            "scan_data": {"category": "cheese"},
            "expect": {"must_flags": ["soft_cheese"]},
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for case in test_data:
            f.write(json.dumps(case) + "\n")
        temp_path = f.name

    try:
        cases = load_cases(temp_path, None)
        assert len(cases) == 2
        assert cases[0]["id"] == "test1"
        assert cases[1]["id"] == "test2"

        # Test limit
        limited = load_cases(temp_path, 1)
        assert len(limited) == 1
        assert limited[0]["id"] == "test1"
    finally:
        os.unlink(temp_path)


def test_check_case_schema() -> None:
    """Test basic schema validation."""
    resp = {
        "summary": "Test summary",
        "disclaimer": "Test disclaimer",
        "reasons": ["reason1"],
        "checks": ["check1"],
        "flags": ["flag1"],
    }
    expect = {}

    ok, errors = check_case(resp, expect)
    assert ok
    assert errors == []

    # Missing required field
    incomplete_resp = {"summary": "Test"}
    ok, errors = check_case(incomplete_resp, expect)
    assert not ok
    assert len(errors) > 0
    assert any("missing key" in err for err in errors)


def test_check_case_must_checks() -> None:
    """Test must_checks validation."""
    resp = {
        "summary": "Test",
        "disclaimer": "Test",
        "reasons": [],
        "checks": ["Check for pasteurisation on label"],
        "flags": [],
    }

    # Should pass
    expect = {"must_checks": ["pasteuris"]}
    ok, errors = check_case(resp, expect)
    assert ok

    # Should fail
    expect = {"must_checks": ["sterilization"]}
    ok, errors = check_case(resp, expect)
    assert not ok
    assert any("missing check contains: sterilization" in err for err in errors)


def test_check_case_must_flags() -> None:
    """Test must_flags validation."""
    resp = {
        "summary": "Test",
        "disclaimer": "Test",
        "reasons": [],
        "checks": [],
        "flags": ["soft_cheese", "contains_peanuts"],
    }

    # Should pass
    expect = {"must_flags": ["soft_cheese"]}
    ok, errors = check_case(resp, expect)
    assert ok

    # Should fail
    expect = {"must_flags": ["missing_flag"]}
    ok, errors = check_case(resp, expect)
    assert not ok
    assert any("missing flag: missing_flag" in err for err in errors)


def test_check_case_must_flags_any() -> None:
    """Test must_flags_any validation."""
    resp = {
        "summary": "Test",
        "disclaimer": "Test",
        "reasons": [],
        "checks": [],
        "flags": ["contains_peanuts"],
    }

    # Should pass - has one of the required flags
    expect = {"must_flags_any": ["contains_peanuts", "contains_nuts"]}
    ok, errors = check_case(resp, expect)
    assert ok

    # Should fail - has none of the required flags
    expect = {"must_flags_any": ["missing_flag1", "missing_flag2"]}
    ok, errors = check_case(resp, expect)
    assert not ok
    assert any("missing any-of flags" in err for err in errors)


def test_check_case_must_reasons() -> None:
    """Test must_reasons validation."""
    resp = {
        "summary": "Test",
        "disclaimer": "Test",
        "reasons": ["This product contains peanuts which may cause allergic reactions"],
        "checks": [],
        "flags": [],
    }

    # Should pass
    expect = {"must_reasons": ["peanut"]}
    ok, errors = check_case(resp, expect)
    assert ok

    # Should fail
    expect = {"must_reasons": ["dairy"]}
    ok, errors = check_case(resp, expect)
    assert not ok
    assert any("missing reason contains: dairy" in err for err in errors)


def test_check_case_evidence() -> None:
    """Test evidence validation."""
    resp = {
        "summary": "Test",
        "disclaimer": "Test",
        "reasons": [],
        "checks": [],
        "flags": [],
        "evidence": [{"type": "recall", "source": "CPSC"}],
    }

    # Should pass
    expect = {"must_evidence": {"type": "recall"}}
    ok, errors = check_case(resp, expect)
    assert ok

    # Should fail
    expect = {"must_evidence": {"type": "regulation"}}
    ok, errors = check_case(resp, expect)
    assert not ok
    assert any("missing evidence type: regulation" in err for err in errors)


def test_dummy_llm_client() -> None:
    """Test that dummy LLM client works."""
    llm = get_llm_client(dummy=True)

    # Test basic response
    resp = llm.chat_json(
        model="test",
        system="test system",
        user="scan_data JSON:\n{'product_name': 'Test Product', 'category': 'cheese', 'flags': ['soft_cheese']}",
        response_schema={},
        timeout=1.0,
    )

    assert "summary" in resp
    assert "disclaimer" in resp
    assert "reasons" in resp
    assert "checks" in resp
    assert "flags" in resp
    assert "soft_cheese" in resp["flags"]
    assert any("pasteuris" in reason.lower() for reason in resp["reasons"])


def test_dummy_llm_peanut_detection() -> None:
    """Test dummy LLM detects peanut allergies."""
    llm = get_llm_client(dummy=True)

    resp = llm.chat_json(
        model="test",
        system="test",
        user="scan_data JSON:\n{'ingredients': ['peanuts'], 'flags': []}",
        response_schema={},
        timeout=1.0,
    )

    assert "contains_peanuts" in resp["flags"]
    assert any("peanut" in reason.lower() for reason in resp["reasons"])


def test_dummy_llm_recall_detection() -> None:
    """Test dummy LLM detects recalls."""
    llm = get_llm_client(dummy=True)

    resp = llm.chat_json(
        model="test",
        system="test",
        user="scan_data JSON:\n{'recalls_found': 1, 'recalls': [{'agency': 'CPSC'}]}",
        response_schema={},
        timeout=1.0,
    )

    assert len(resp["evidence"]) > 0
    assert resp["evidence"][0]["type"] == "recall"
    assert any("recall" in reason.lower() for reason in resp["reasons"])
