"""
Unit tests for authentication system
"""

import pytest
from core_infra.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
    SecureToken
)
from core_infra.encryption import EncryptionManager
from datetime import timedelta

class TestPasswordHashing:
    """Test password hashing and verification"""
    
    def test_password_hash(self):
        """Test password hashing"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Hash should be verifiable
        assert verify_password(password, hashed)
    
    def test_wrong_password(self):
        """Test wrong password verification"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = get_password_hash(password)
        
        assert not verify_password(wrong_password, hashed)
    
    def test_same_password_different_hash(self):
        """Test that same password produces different hashes"""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTTokens:
    """Test JWT token creation and validation"""
    
    def test_create_access_token(self):
        """Test access token creation"""
        data = {"sub": 123, "email": "test@example.com"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_valid_token(self):
        """Test decoding valid token"""
        data = {"sub": 123}
        token = create_access_token(data)
        
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == 123
        assert "exp" in decoded
        assert decoded["type"] == "access"
    
    def test_decode_invalid_token(self):
        """Test decoding invalid token"""
        invalid_token = "invalid.token.here"
        decoded = decode_token(invalid_token)
        
        assert decoded is None
    
    def test_token_expiration(self):
        """Test token expiration"""
        data = {"sub": 123}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        decoded = decode_token(token)
        # Should be None because token is expired
        assert decoded is None


class TestEncryption:
    """Test PII encryption"""
    
    def test_string_encryption(self):
        """Test string encryption and decryption"""
        manager = EncryptionManager()
        original = "sensitive@email.com"
        
        encrypted = manager.encrypt(original)
        assert encrypted != original
        
        decrypted = manager.decrypt(encrypted)
        assert decrypted == original
    
    def test_dict_encryption(self):
        """Test dictionary encryption"""
        manager = EncryptionManager()
        original = {
            "email": "test@example.com",
            "ssn": "123-45-6789"
        }
        
        encrypted = manager.encrypt_dict(original)
        assert isinstance(encrypted, str)
        
        decrypted = manager.decrypt_dict(encrypted)
        assert decrypted == original
    
    def test_empty_encryption(self):
        """Test encryption of empty values"""
        manager = EncryptionManager()
        
        assert manager.encrypt(None) is None
        assert manager.encrypt("") is None
        assert manager.decrypt(None) is None


class TestSecureTokens:
    """Test secure token generation"""
    
    def test_token_generation(self):
        """Test secure token generation"""
        token1 = SecureToken.generate()
        token2 = SecureToken.generate()
        
        # Tokens should be unique
        assert token1 != token2
        
        # Tokens should have expected length
        assert len(token1) > 20
    
    def test_numeric_token(self):
        """Test numeric token generation"""
        token = SecureToken.generate_numeric(6)
        
        assert len(token) == 6
        assert token.isdigit()
    
    def test_token_hashing(self):
        """Test token hashing and verification"""
        token = "test_token_123"
        hashed = SecureToken.hash_token(token)
        
        assert hashed != token
        assert SecureToken.verify_token(token, hashed)
        assert not SecureToken.verify_token("wrong_token", hashed)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
