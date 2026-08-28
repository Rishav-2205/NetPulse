"""
Unit Tests: Payload Generators & Checksum Validation.
"""

import pytest

from app.core.exceptions import PacketValidationError
from app.packets.builder import PayloadGenerator


@pytest.mark.unit
class TestPayloadGenerator:
    """Test suite for deterministic test payloads and checksum calculators."""

    def test_payload_sizes(self) -> None:
        """Test standard payload sizes."""
        small = PayloadGenerator.generate_small()
        medium = PayloadGenerator.generate_medium()
        large = PayloadGenerator.generate_large()

        assert len(small) == 64
        assert len(medium) == 1024
        assert len(large) == 65536

    def test_deterministic_generation_reproducibility(self) -> None:
        """Test that same random seed produces byte-for-byte identical output."""
        p1 = PayloadGenerator.generate_random(size=512, seed=999)
        p2 = PayloadGenerator.generate_random(size=512, seed=999)
        assert p1 == p2

        p3 = PayloadGenerator.generate_random(size=512, seed=123)
        assert p1 != p3

    def test_binary_pattern_generation(self) -> None:
        """Test repeated pattern payload generation."""
        pattern = b"\x00\xff"
        payload = PayloadGenerator.generate_binary_pattern(size=10, pattern=pattern)
        assert len(payload) == 10
        assert payload == b"\x00\xff\x00\xff\x00\xff\x00\xff\x00\xff"

    def test_checksum_algorithms(self) -> None:
        """Test SHA-256, MD5, and CRC32 checksum calculations."""
        data = b"NetPulse Checksum Verification Data"
        sha = PayloadGenerator.calculate_checksum(data, algorithm="sha256")
        md5 = PayloadGenerator.calculate_checksum(data, algorithm="md5")
        crc = PayloadGenerator.calculate_checksum(data, algorithm="crc32")

        assert len(sha) == 64
        assert len(md5) == 32
        assert len(crc) == 8

        assert PayloadGenerator.verify_checksum(data, sha, algorithm="sha256") is True

    def test_checksum_mismatch_raises_error(self) -> None:
        """Test that checksum mismatch raises PacketValidationError."""
        data = b"Original Data"
        with pytest.raises(PacketValidationError) as exc_info:
            PayloadGenerator.verify_checksum(data, "0000000000000000000000000000000000000000000000000000000000000000")
        assert "Checksum mismatch" in str(exc_info.value)
