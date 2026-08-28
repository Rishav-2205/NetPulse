"""
Unit Tests: Configuration System.
"""

import os
import pytest

from app.core.config import ConfigManager, AppConfig
from app.core.exceptions import ConfigurationError


@pytest.mark.unit
class TestConfigManager:
    """Test suite covering configuration loading, merging, and validation."""

    def setup_method(self) -> None:
        ConfigManager.reset()

    def teardown_method(self) -> None:
        ConfigManager.reset()

    def test_default_config_loading(self) -> None:
        """Test loading standard default configuration values."""
        cfg = ConfigManager.load()
        assert isinstance(cfg, AppConfig)
        assert cfg.network.tcp_timeout == 5.0
        assert cfg.network.udp_timeout == 3.0
        assert cfg.testing.retries == 2
        assert cfg.profile_name == "default"

    def test_profile_override_loading(self) -> None:
        """Test loading with 'fast' profile overrides."""
        cfg = ConfigManager.load(profile="fast")
        assert cfg.profile_name == "fast"
        assert cfg.network.tcp_timeout == 1.5
        assert cfg.testing.retries == 1

    def test_environment_variable_override(self) -> None:
        """Test overriding configuration settings via NETPULSE_* environment variables."""
        os.environ["NETPULSE_NETWORK_TCP_TIMEOUT"] = "12.5"
        os.environ["NETPULSE_TESTING_RETRIES"] = "7"
        try:
            cfg = ConfigManager.load()
            assert cfg.network.tcp_timeout == 12.5
            assert cfg.testing.retries == 7
        finally:
            os.environ.pop("NETPULSE_NETWORK_TCP_TIMEOUT", None)
            os.environ.pop("NETPULSE_TESTING_RETRIES", None)

    def test_invalid_configuration_rejection(self) -> None:
        """Test that invalid configuration values trigger ConfigurationError."""
        os.environ["NETPULSE_NETWORK_TCP_TIMEOUT"] = "-1.0"
        try:
            with pytest.raises(ConfigurationError) as exc_info:
                ConfigManager.load()
            assert "tcp_timeout must be > 0" in str(exc_info.value)
        finally:
            os.environ.pop("NETPULSE_NETWORK_TCP_TIMEOUT", None)
