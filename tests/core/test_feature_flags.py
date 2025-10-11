import pytest
import os
from unittest.mock import patch
from core.feature_flags import env_bool, env_float, chat_enabled_for, _bucket


class TestEnvHelpers:
    def test_env_bool_default_false(self):
        with patch.dict(os.environ, {}, clear=True):
            assert env_bool("MISSING_VAR") is False

    def test_env_bool_default_true(self):
        with patch.dict(os.environ, {}, clear=True):
            assert env_bool("MISSING_VAR", default=True) is True

    def test_env_bool_truthy_values(self):
        for val in ["1", "true", "TRUE", "yes", "YES", "on", "ON"]:
            with patch.dict(os.environ, {"TEST_VAR": val}):
                assert env_bool("TEST_VAR") is True

    def test_env_bool_falsy_values(self):
        for val in ["0", "false", "FALSE", "no", "NO", "off", "OFF", "random"]:
            with patch.dict(os.environ, {"TEST_VAR": val}):
                assert env_bool("TEST_VAR") is False

    def test_env_float_default(self):
        with patch.dict(os.environ, {}, clear=True):
            assert env_float("MISSING_VAR", 3.14) == 3.14

    def test_env_float_valid(self):
        with patch.dict(os.environ, {"TEST_VAR": "2.5"}):
            assert env_float("TEST_VAR") == 2.5

    def test_env_float_invalid_returns_default(self):
        with patch.dict(os.environ, {"TEST_VAR": "not_a_number"}):
            assert env_float("TEST_VAR", 1.0) == 1.0


class TestBucketFunction:
    def test_bucket_deterministic(self):
        # Same input should always give same output
        assert _bucket("user123") == _bucket("user123")

    def test_bucket_range(self):
        # Should return values between 0.0 and 1.0
        for user_id in ["user1", "user2", "user3", "test@example.com", "device_abc123"]:
            bucket_val = _bucket(user_id)
            assert 0.0 <= bucket_val <= 1.0

    def test_bucket_distribution(self):
        # Different inputs should generally give different outputs
        buckets = [_bucket(f"user{i}") for i in range(100)]
        unique_buckets = set(buckets)
        # Should have good distribution (at least 80% unique for 100 users)
        assert len(unique_buckets) > 80


class TestChatEnabledFor:
    def test_disabled_globally(self):
        with patch("core.feature_flags.FEATURE_CHAT_ENABLED", False):
            assert chat_enabled_for("user123") is False
            assert chat_enabled_for("user123", "device456") is False

    def test_no_user_or_device_id(self):
        with patch("core.feature_flags.FEATURE_CHAT_ENABLED", True):
            assert chat_enabled_for(None) is False
            assert chat_enabled_for("") is False
            assert chat_enabled_for(None, None) is False
            assert chat_enabled_for("", "") is False

    def test_rollout_percentage(self):
        with patch("core.feature_flags.FEATURE_CHAT_ENABLED", True):
            # Test 0% rollout
            with patch("core.feature_flags.FEATURE_CHAT_ROLLOUT_PCT", 0.0):
                assert chat_enabled_for("user123") is False

            # Test 100% rollout
            with patch("core.feature_flags.FEATURE_CHAT_ROLLOUT_PCT", 1.0):
                assert chat_enabled_for("user123") is True

            # Test specific user that should be in 10% bucket
            # We need to find a user that hashes to < 0.1
            with patch("core.feature_flags.FEATURE_CHAT_ROLLOUT_PCT", 0.1):
                # Test a bunch of users to find one in the 10% bucket
                found_enabled = False
                found_disabled = False
                for i in range(100):
                    user_id = f"testuser{i}"
                    if chat_enabled_for(user_id):
                        found_enabled = True
                    else:
                        found_disabled = True
                    if found_enabled and found_disabled:
                        break

                # With 100 users and 10% rollout, we should find both enabled and disabled
                assert found_enabled, "Should find at least one user in 10% rollout"
                assert found_disabled, "Should find at least one user NOT in 10% rollout"

    def test_prefers_user_id_over_device_id(self):
        with patch("core.feature_flags.FEATURE_CHAT_ENABLED", True):
            with patch("core.feature_flags.FEATURE_CHAT_ROLLOUT_PCT", 1.0):
                # Both should work
                assert chat_enabled_for("user123", "device456") is True
                assert chat_enabled_for(None, "device456") is True

                # But user_id takes precedence (same result regardless of device_id)
                result1 = chat_enabled_for("user123", "device456")
                result2 = chat_enabled_for("user123", "different_device")
                assert result1 == result2

    def test_sticky_rollout(self):
        """Test that the same user always gets the same result"""
        with patch("core.feature_flags.FEATURE_CHAT_ENABLED", True):
            with patch("core.feature_flags.FEATURE_CHAT_ROLLOUT_PCT", 0.5):
                # Same user should always get same result
                user_id = "consistent_user"
                result1 = chat_enabled_for(user_id)
                result2 = chat_enabled_for(user_id)
                result3 = chat_enabled_for(user_id)

                assert result1 == result2 == result3
