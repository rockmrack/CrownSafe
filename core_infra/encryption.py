"""
PII Encryption for BabyShield
Protects sensitive user data with AES encryption
"""

import base64
import hashlib
import json
import os
import secrets

from cryptography.fernet import Fernet
from sqlalchemy.types import String, Text, TypeDecorator

# Get or generate encryption key
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    # Generate a key for development (DO NOT USE IN PRODUCTION)
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print("⚠️ Generated development encryption key. Set ENCRYPTION_KEY env var for production!")


class EncryptionManager:
    """
    Manages encryption/decryption of sensitive data
    """

    def __init__(self, key: str = None):
        if key:
            self.key = key.encode() if isinstance(key, str) else key
        else:
            self.key = ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY

        self.cipher = Fernet(self.key)

    def encrypt(self, data: str) -> str:
        """
        Encrypt string data
        """
        if not data:
            return None

        encrypted = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt string data
        """
        if not encrypted_data:
            return None

        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            # Log error but don't expose encryption errors
            print(f"Decryption error: {e}")
            return None

    def encrypt_dict(self, data: dict) -> str:
        """
        Encrypt dictionary as JSON
        """
        json_str = json.dumps(data)
        return self.encrypt(json_str)

    def decrypt_dict(self, encrypted_data: str) -> dict:
        """
        Decrypt JSON dictionary
        """
        decrypted = self.decrypt(encrypted_data)
        if decrypted:
            return json.loads(decrypted)
        return {}


# Global encryption manager
encryption_manager = EncryptionManager()


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy type for encrypted string columns
    Automatically encrypts/decrypts on save/load
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """
        Encrypt before saving to database
        """
        if value is not None:
            return encryption_manager.encrypt(value)
        return value

    def process_result_value(self, value, dialect):
        """
        Decrypt after loading from database
        """
        if value is not None:
            return encryption_manager.decrypt(value)
        return value


class HashedString(TypeDecorator):
    """
    SQLAlchemy type for one-way hashed strings
    Used for data that needs to be searchable but not readable
    """

    impl = String(64)  # SHA-256 produces 64 character hex
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """
        Hash before saving
        """
        if value is not None:
            return hashlib.sha256(value.encode()).hexdigest()
        return value

    def process_result_value(self, value, dialect):
        """
        Return hash (cannot be reversed)
        """
        return value


class EncryptedJSON(TypeDecorator):
    """
    SQLAlchemy type for encrypted JSON columns
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """
        Encrypt JSON before saving
        """
        if value is not None:
            return encryption_manager.encrypt_dict(value)
        return value

    def process_result_value(self, value, dialect):
        """
        Decrypt JSON after loading
        """
        if value is not None:
            return encryption_manager.decrypt_dict(value)
        return value


def mask_pii(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Mask PII data for display (e.g., email: j****@example.com)
    """
    if not data or len(data) <= visible_chars:
        return data

    if "@" in data:  # Email
        parts = data.split("@")
        if len(parts) == 2:
            username = parts[0]
            domain = parts[1]
            if len(username) > 2:
                masked_username = username[0] + mask_char * (len(username) - 2) + username[-1]
            else:
                masked_username = mask_char * len(username)
            return f"{masked_username}@{domain}"

    # Generic masking
    visible_start = visible_chars // 2
    visible_end = visible_chars - visible_start

    if len(data) > visible_chars:
        masked_middle = mask_char * (len(data) - visible_chars)
        return data[:visible_start] + masked_middle + data[-visible_end:]

    return data


def anonymize_data(data: dict, fields_to_anonymize: list) -> dict:
    """
    Anonymize specific fields in a dictionary
    """
    anonymized = data.copy()

    for field in fields_to_anonymize:
        if field in anonymized:
            if isinstance(anonymized[field], str):
                # Generate consistent anonymous value
                anonymized[field] = f"anon_{hashlib.md5(anonymized[field].encode()).hexdigest()[:8]}"
            elif isinstance(anonymized[field], (int, float)):
                # Randomize numeric values
                anonymized[field] = hash(str(anonymized[field])) % 1000000

    return anonymized


class PIIRedactor:
    """
    Redact PII from text using patterns
    """

    PII_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    }

    @classmethod
    def redact(cls, text: str, patterns: list = None) -> str:
        """
        Redact PII from text
        """
        import re

        if not text:
            return text

        patterns_to_use = patterns or cls.PII_PATTERNS.keys()
        result = text

        for pattern_name in patterns_to_use:
            if pattern_name in cls.PII_PATTERNS:
                pattern = cls.PII_PATTERNS[pattern_name]
                result = re.sub(pattern, f"[REDACTED_{pattern_name.upper()}]", result)

        return result


def encrypt_file(file_path: str, output_path: str = None):
    """
    Encrypt a file
    """
    if not output_path:
        output_path = f"{file_path}.encrypted"

    with open(file_path, "rb") as f:
        data = f.read()

    encrypted = encryption_manager.cipher.encrypt(data)

    with open(output_path, "wb") as f:
        f.write(encrypted)

    return output_path


def decrypt_file(encrypted_path: str, output_path: str = None):
    """
    Decrypt a file
    """
    if not output_path:
        output_path = encrypted_path.replace(".encrypted", "")

    with open(encrypted_path, "rb") as f:
        encrypted_data = f.read()

    decrypted = encryption_manager.cipher.decrypt(encrypted_data)

    with open(output_path, "wb") as f:
        f.write(decrypted)

    return output_path


class SecureToken:
    """
    Generate and verify secure tokens
    """

    @staticmethod
    def generate(length: int = 32) -> str:
        """
        Generate a secure random token
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_numeric(length: int = 6) -> str:
        """
        Generate numeric token (e.g., for SMS codes)
        """
        return "".join(secrets.choice("0123456789") for _ in range(length))

    @staticmethod
    def hash_token(token: str) -> str:
        """
        Hash a token for storage
        """
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def verify_token(token: str, hashed: str) -> bool:
        """
        Verify a token against its hash
        """
        return SecureToken.hash_token(token) == hashed


# Example usage in models
"""
from sqlalchemy import Column, Integer
from core_infra.database import Base
from core_infra.encryption import EncryptedString, EncryptedJSON, HashedString

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(EncryptedString)  # Encrypted email
    email_hash = Column(HashedString)  # For searching
    personal_data = Column(EncryptedJSON)  # Encrypted JSON
    
    def set_email(self, email: str):
        self.email = email
        self.email_hash = email  # Will be hashed automatically
"""
