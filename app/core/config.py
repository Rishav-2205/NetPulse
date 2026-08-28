"""
NetPulse Configuration System.

Provides dataclass-backed configurations, YAML loading with profile support,
environment variable overrides, schema validation, and path resolution.
"""

from dataclasses import dataclass, field, asdict
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from app.core.exceptions import ConfigurationError


@dataclass
class NetworkConfig:
    """Network connection and protocol settings."""
    tcp_timeout: float = 5.0
    udp_timeout: float = 3.0
    http_timeout: float = 5.0
    buffer_size: int = 4096
    default_host: str = "127.0.0.1"
    default_port: int = 5001
    tcp_nodelay: bool = True
    so_reuseaddr: bool = True
    connection_retries: int = 2
    max_payload_size: int = 1048576  # 1MB


@dataclass
class TestingConfig:
    """Test orchestration and execution settings."""
    retries: int = 2
    retry_backoff_factor: float = 1.5
    retry_initial_delay: float = 0.2
    packet_count: int = 100
    default_port: int = 5001
    ephemeral_port: int = 0
    duration_seconds: float = 5.0
    baseline_file: str = "reports/baseline.json"
    results_file: str = "reports/results.json"
    junit_file: str = "reports/junit.xml"
    html_report_file: str = "reports/report.html"


@dataclass
class LoggingConfig:
    """Structured logging configuration."""
    level: str = "INFO"
    file: str = "logs/netpulse.log"
    json_file: str = "logs/netpulse.json.log"
    console: bool = True
    structured: bool = True


@dataclass
class TopologyConfig:
    """Simulated topology parameters."""
    default_mtu: int = 1500
    default_latency_ms: float = 1.0
    default_loss_pct: float = 0.0
    default_bandwidth_mbps: float = 1000.0


@dataclass
class PerformanceConfig:
    """Performance testing and benchmark parameters."""
    duration: float = 2.0
    packet_count: int = 1000
    packet_sizes: List[int] = field(default_factory=lambda: [64, 1024, 8192])
    concurrency: int = 1
    throughput_drop_threshold_pct: float = 15.0
    latency_increase_threshold_pct: float = 20.0
    packet_loss_threshold_pct: float = 1.0


@dataclass
class AppConfig:
    """Root configuration object containing all component configs."""
    network: NetworkConfig = field(default_factory=NetworkConfig)
    testing: TestingConfig = field(default_factory=TestingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    topology: TopologyConfig = field(default_factory=TopologyConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    profile_name: str = "default"

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire config to dictionary."""
        return asdict(self)


class ConfigManager:
    """
    Manages loading, merging, environment overriding, and validating NetPulse configuration.
    """

    _instance: Optional[AppConfig] = None

    @classmethod
    def get_workspace_root(cls) -> Path:
        """Find the root directory of the repository."""
        curr = Path(__file__).resolve()
        for parent in curr.parents:
            if (parent / "configs").exists() or (parent / "pyproject.toml").exists():
                return parent
        return Path.cwd()

    @classmethod
    def load(
        cls,
        config_path: Optional[str] = None,
        profile: Optional[str] = None,
        env_prefix: str = "NETPULSE_"
    ) -> AppConfig:
        """
        Load configuration from YAML file, apply profile overrides and environment variables.
        """
        root = cls.get_workspace_root()
        default_config_path = root / "configs" / "default.yaml"
        profiles_path = root / "configs" / "test_profiles.yaml"

        config_data: Dict[str, Any] = {}

        # 1. Load default config file if present
        target_path = Path(config_path) if config_path else default_config_path
        if target_path.exists():
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                    if isinstance(loaded, dict):
                        config_data = loaded
            except Exception as e:
                raise ConfigurationError(f"Failed to parse configuration file at {target_path}: {e}") from e

        # 2. Merge Profile if specified
        if profile:
            if profiles_path.exists():
                try:
                    with open(profiles_path, "r", encoding="utf-8") as f:
                        profiles_data = yaml.safe_load(f)
                        if isinstance(profiles_data, dict) and profile in profiles_data:
                            cls._deep_merge(config_data, profiles_data[profile])
                        elif isinstance(profiles_data, dict):
                            raise ConfigurationError(f"Profile '{profile}' not found in {profiles_path}")
                except ConfigurationError:
                    raise
                except Exception as e:
                    raise ConfigurationError(f"Failed to parse profiles file at {profiles_path}: {e}") from e
            else:
                raise ConfigurationError(f"Profiles file not found at {profiles_path}")

        # 3. Build sub-dataclasses
        net_kwargs = config_data.get("network", {})
        test_kwargs = config_data.get("testing", {})
        log_kwargs = config_data.get("logging", {})
        top_kwargs = config_data.get("topology", {})
        perf_kwargs = config_data.get("performance", {})

        network_cfg = NetworkConfig(**{k: v for k, v in net_kwargs.items() if hasattr(NetworkConfig, k)})
        testing_cfg = TestingConfig(**{k: v for k, v in test_kwargs.items() if hasattr(TestingConfig, k)})
        logging_cfg = LoggingConfig(**{k: v for k, v in log_kwargs.items() if hasattr(LoggingConfig, k)})
        topology_cfg = TopologyConfig(**{k: v for k, v in top_kwargs.items() if hasattr(TopologyConfig, k)})
        performance_cfg = PerformanceConfig(**{k: v for k, v in perf_kwargs.items() if hasattr(PerformanceConfig, k)})

        # 4. Apply environment variable overrides (e.g., NETPULSE_NETWORK_TCP_TIMEOUT=10)
        cls._apply_env_overrides(network_cfg, "NETWORK_", env_prefix)
        cls._apply_env_overrides(testing_cfg, "TESTING_", env_prefix)
        cls._apply_env_overrides(logging_cfg, "LOGGING_", env_prefix)
        cls._apply_env_overrides(topology_cfg, "TOPOLOGY_", env_prefix)
        cls._apply_env_overrides(performance_cfg, "PERFORMANCE_", env_prefix)

        app_config = AppConfig(
            network=network_cfg,
            testing=testing_cfg,
            logging=logging_cfg,
            topology=topology_cfg,
            performance=performance_cfg,
            profile_name=profile or "default"
        )

        cls._validate_config(app_config)
        cls._instance = app_config
        return app_config

    @classmethod
    def get_config(cls) -> AppConfig:
        """Retrieve the cached singleton configuration or load the default."""
        if cls._instance is None:
            cls._instance = cls.load()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance."""
        cls._instance = None

    @staticmethod
    def _deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Recursively merge update dictionary into base dictionary."""
        for k, v in update.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                ConfigManager._deep_merge(base[k], v)
            else:
                base[k] = v

    @staticmethod
    def _apply_env_overrides(target: Any, section_prefix: str, global_prefix: str) -> None:
        """Override dataclass fields from environment variables."""
        full_prefix = f"{global_prefix}{section_prefix}"
        for field_name in target.__dataclass_fields__:
            env_key = f"{full_prefix}{field_name.upper()}"
            if env_key in os.environ:
                val_str = os.environ[env_key]
                current_val = getattr(target, field_name)
                # Type cast
                if isinstance(current_val, bool):
                    setattr(target, field_name, val_str.lower() in ("1", "true", "yes", "on"))
                elif isinstance(current_val, int):
                    setattr(target, field_name, int(val_str))
                elif isinstance(current_val, float):
                    setattr(target, field_name, float(val_str))
                else:
                    setattr(target, field_name, val_str)

    @staticmethod
    def _validate_config(config: AppConfig) -> None:
        """Validate configuration constraints."""
        if config.network.tcp_timeout <= 0:
            raise ConfigurationError(f"network.tcp_timeout must be > 0, got {config.network.tcp_timeout}")
        if config.network.udp_timeout <= 0:
            raise ConfigurationError(f"network.udp_timeout must be > 0, got {config.network.udp_timeout}")
        if config.network.buffer_size <= 0:
            raise ConfigurationError(f"network.buffer_size must be > 0, got {config.network.buffer_size}")
        if not (0 <= config.network.default_port <= 65535):
            raise ConfigurationError(f"network.default_port must be in 0-65535, got {config.network.default_port}")
        if config.testing.retries < 0:
            raise ConfigurationError(f"testing.retries must be >= 0, got {config.testing.retries}")
        if config.topology.default_mtu < 68:
            raise ConfigurationError(f"topology.default_mtu must be >= 68, got {config.topology.default_mtu}")
        if not (0.0 <= config.topology.default_loss_pct <= 100.0):
            raise ConfigurationError(f"topology.default_loss_pct must be between 0 and 100, got {config.topology.default_loss_pct}")
