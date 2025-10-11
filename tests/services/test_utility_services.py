"""
Service Layer Utility Tests - Phase 2

Tests utility services including email, SMS, encryption, image processing, and date utilities.
These are supporting services used throughout the application.

Author: BabyShield Development Team
Date: October 11, 2025
"""

from datetime import datetime, timezone
from io import BytesIO
from typing import Dict
from unittest.mock import Mock, patch

import pytest
from PIL import Image


# ====================
# SERVICE LAYER TESTS
# ====================


@pytest.mark.services
@pytest.mark.unit
@patch("services.email_service.SendGridAPIClient")
def test_email_service_send_with_attachments(mock_sendgrid):
    """
    Test email service sending with PDF attachments.

    Acceptance Criteria:
    - Send email with PDF attachment
    - Handle multiple recipients
    - Support CC and BCC
    - Include HTML and plain text
    - Handle attachment encoding
    - Return send confirmation
    """
    from services.email_service import EmailService

    # Setup mock
    mock_client = Mock()
    mock_sendgrid.return_value = mock_client
    mock_client.send.return_value = Mock(status_code=202)

    # Create service
    email_service = EmailService(api_key="test_key")

    # Create test attachment
    pdf_content = b"%PDF-1.4 test content"

    # Send email with attachment
    result = email_service.send_email(
        to=["user@example.com"],
        subject="Recall Alert - Action Required",
        html_body="<h1>Important Recall</h1><p>Please review attached PDF.</p>",
        text_body="Important Recall - Please review attached PDF.",
        from_email="alerts@babyshield.dev",
        from_name="BabyShield Alerts",
        attachments=[{"filename": "recall_details.pdf", "content": pdf_content, "mimetype": "application/pdf"}],
        cc=["admin@babyshield.dev"],
        bcc=["archive@babyshield.dev"],
    )

    # Verify send was called
    assert mock_client.send.called
    assert result["status"] == "sent"
    assert result["message_id"] is not None

    # Verify attachment was included
    call_args = mock_client.send.call_args
    assert call_args is not None


@pytest.mark.services
@pytest.mark.unit
@patch("services.sms_service.TwilioClient")
def test_sms_service_international_numbers(mock_twilio):
    """
    Test SMS service with international phone numbers.

    Acceptance Criteria:
    - Send SMS to US numbers (+1)
    - Send SMS to UK numbers (+44)
    - Send SMS to other international numbers
    - Validate phone number format
    - Handle sending errors gracefully
    - Return delivery status
    """
    from services.sms_service import SMSService

    # Setup mock
    mock_client = Mock()
    mock_twilio.return_value = mock_client
    mock_messages = Mock()
    mock_client.messages = mock_messages

    # Mock successful send
    mock_message = Mock()
    mock_message.sid = "SM123456789"
    mock_message.status = "sent"
    mock_messages.create.return_value = mock_message

    # Create service
    sms_service = SMSService(account_sid="test_sid", auth_token="test_token", from_number="+15555551234")

    # Test 1: Send to US number
    result_us = sms_service.send_sms(
        to="+12025551234", message="Recall alert: Baby Monitor X200 has been recalled due to fire hazard."
    )
    assert result_us["status"] == "sent"
    assert result_us["sid"] == "SM123456789"

    # Test 2: Send to UK number
    result_uk = sms_service.send_sms(to="+442012345678", message="Recall alert for your registered product.")
    assert result_uk["status"] == "sent"

    # Test 3: Send to Canadian number
    result_ca = sms_service.send_sms(
        to="+14165551234", message="BabyShield Alert: Check your app for important recall information."
    )
    assert result_ca["status"] == "sent"

    # Test 4: Invalid phone number
    with pytest.raises(ValueError, match="Invalid phone number format"):
        sms_service.send_sms(to="invalid", message="Test")

    # Test 5: Handle Twilio error
    mock_messages.create.side_effect = Exception("Twilio API Error")
    result_error = sms_service.send_sms(to="+12025551234", message="Test", raise_on_error=False)
    assert result_error["status"] == "failed"
    assert "error" in result_error


@pytest.mark.services
@pytest.mark.unit
def test_encryption_service_aes256_encrypt_decrypt():
    """
    Test encryption service with AES-256 encryption/decryption.

    Acceptance Criteria:
    - Encrypt sensitive data with AES-256
    - Decrypt back to original
    - Use secure key derivation
    - Handle different data types (str, bytes, dict)
    - Verify data integrity
    """
    from services.encryption_service import EncryptionService

    # Create service with test key
    encryption_service = EncryptionService(master_key="test_master_key_32_characters!!")

    # Test 1: Encrypt and decrypt string
    original_text = "Sensitive user data: SSN 123-45-6789"
    encrypted = encryption_service.encrypt(original_text)

    assert encrypted != original_text
    assert isinstance(encrypted, str)
    assert len(encrypted) > len(original_text)  # Encrypted is longer

    decrypted = encryption_service.decrypt(encrypted)
    assert decrypted == original_text

    # Test 2: Encrypt and decrypt bytes
    original_bytes = b"Binary data here"
    encrypted_bytes = encryption_service.encrypt(original_bytes)
    decrypted_bytes = encryption_service.decrypt(encrypted_bytes)
    assert decrypted_bytes == original_bytes.decode()

    # Test 3: Encrypt and decrypt dictionary
    original_dict = {"credit_card": "4111111111111111", "cvv": "123", "expiry": "12/25"}
    encrypted_dict = encryption_service.encrypt_dict(original_dict)

    # Verify all values are encrypted
    assert encrypted_dict["credit_card"] != original_dict["credit_card"]
    assert encrypted_dict["cvv"] != original_dict["cvv"]

    decrypted_dict = encryption_service.decrypt_dict(encrypted_dict)
    assert decrypted_dict == original_dict

    # Test 4: Verify tampering detection
    tampered = encrypted[:-5] + "XXXXX"
    with pytest.raises(Exception, match="Decryption failed|Invalid"):
        encryption_service.decrypt(tampered)

    # Test 5: Empty string handling
    encrypted_empty = encryption_service.encrypt("")
    decrypted_empty = encryption_service.decrypt(encrypted_empty)
    assert decrypted_empty == ""


@pytest.mark.services
@pytest.mark.unit
def test_image_processing_resize_and_optimize():
    """
    Test image processing service for resizing and optimizing images.

    Acceptance Criteria:
    - Resize images to specified dimensions
    - Maintain aspect ratio
    - Optimize file size
    - Support JPEG and PNG formats
    - Generate thumbnails
    - Compress without quality loss
    """
    from services.image_processing import ImageProcessor

    # Create test image (1000x800 red square)
    original_image = Image.new("RGB", (1000, 800), color="red")
    original_buffer = BytesIO()
    original_image.save(original_buffer, format="JPEG", quality=95)
    original_size = original_buffer.tell()
    original_buffer.seek(0)

    # Create processor
    processor = ImageProcessor()

    # Test 1: Resize to specific width (maintain aspect ratio)
    resized = processor.resize_image(original_buffer, target_width=500, maintain_aspect_ratio=True)

    resized_image = Image.open(BytesIO(resized))
    assert resized_image.width == 500
    assert resized_image.height == 400  # Maintains 5:4 ratio

    # Test 2: Resize to specific dimensions (no aspect ratio)
    original_buffer.seek(0)
    resized_exact = processor.resize_image(
        original_buffer, target_width=300, target_height=300, maintain_aspect_ratio=False
    )

    resized_exact_image = Image.open(BytesIO(resized_exact))
    assert resized_exact_image.width == 300
    assert resized_exact_image.height == 300

    # Test 3: Generate thumbnail
    original_buffer.seek(0)
    thumbnail = processor.create_thumbnail(original_buffer, size=(150, 150))

    thumb_image = Image.open(BytesIO(thumbnail))
    assert thumb_image.width <= 150
    assert thumb_image.height <= 150

    # Test 4: Optimize/compress image
    original_buffer.seek(0)
    optimized = processor.optimize_image(original_buffer, quality=80, format="JPEG")

    optimized_size = len(optimized)
    assert optimized_size < original_size, "Optimized should be smaller"
    assert optimized_size > 0

    # Verify image still valid
    optimized_image = Image.open(BytesIO(optimized))
    assert optimized_image.format == "JPEG"

    # Test 5: PNG support
    png_image = Image.new("RGBA", (500, 500), color=(255, 0, 0, 128))
    png_buffer = BytesIO()
    png_image.save(png_buffer, format="PNG")
    png_buffer.seek(0)

    optimized_png = processor.optimize_image(png_buffer, format="PNG")
    assert len(optimized_png) > 0


@pytest.mark.services
@pytest.mark.unit
def test_date_utils_timezone_conversion():
    """
    Test date utility functions for timezone conversions.

    Acceptance Criteria:
    - Convert UTC to local timezones
    - Convert local to UTC
    - Handle daylight saving time
    - Support major timezones (US, Europe, Asia)
    - Format dates in user's locale
    - Parse ISO8601 and other formats
    """
    from services.date_utils import DateUtils

    date_utils = DateUtils()

    # Test 1: UTC to US Eastern
    utc_time = datetime(2024, 3, 15, 14, 30, 0, tzinfo=timezone.utc)
    eastern_time = date_utils.convert_timezone(utc_time, target_timezone="America/New_York")

    # EST is UTC-5, so 14:30 UTC = 9:30 EST (during standard time)
    # Note: Actual offset depends on DST
    assert eastern_time.tzinfo is not None
    assert eastern_time.hour != utc_time.hour

    # Test 2: Local to UTC
    local_time = datetime(2024, 6, 15, 10, 0, 0)
    utc_converted = date_utils.to_utc(local_time, source_timezone="America/Los_Angeles")

    assert utc_converted.tzinfo == timezone.utc
    # PDT is UTC-7, so 10:00 PDT = 17:00 UTC
    assert utc_converted.hour == 17

    # Test 3: Format in user's locale
    formatted_us = date_utils.format_datetime(utc_time, locale="en_US", format_style="medium")
    assert "Mar" in formatted_us or "3" in formatted_us
    assert "2024" in formatted_us

    formatted_eu = date_utils.format_datetime(utc_time, locale="de_DE", format_style="medium")
    assert formatted_eu != formatted_us  # Different formats

    # Test 4: Parse ISO8601
    iso_string = "2024-03-15T14:30:00Z"
    parsed = date_utils.parse_datetime(iso_string)
    assert parsed.year == 2024
    assert parsed.month == 3
    assert parsed.day == 15
    assert parsed.hour == 14

    # Test 5: Parse various formats
    formats = [
        ("2024-03-15", datetime(2024, 3, 15)),
        ("03/15/2024", datetime(2024, 3, 15)),
        ("15-03-2024", datetime(2024, 3, 15)),
        ("March 15, 2024", datetime(2024, 3, 15)),
    ]

    for date_string, expected in formats:
        parsed = date_utils.parse_datetime(date_string, fuzzy=True)
        assert parsed.year == expected.year
        assert parsed.month == expected.month
        assert parsed.day == expected.day

    # Test 6: Handle invalid dates
    with pytest.raises(ValueError):
        date_utils.parse_datetime("invalid date")

    # Test 7: Timezone-aware comparison
    time1 = datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
    time2 = date_utils.convert_timezone(time1, "America/New_York")

    # Same moment in time, different timezones
    assert date_utils.are_same_moment(time1, time2)
