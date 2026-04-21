import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class WatchdogConfig:
    """Configuration for the Saikou Watchdog service monitor."""

    targets: List[str] = field(default_factory=list)

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 5.0
    timeout: float = 10.0

    # Check interval
    check_interval: float = 60.0

    # Slack
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = "#alerts"

    # Logging
    log_file: str = "watchdog.log"
    log_max_bytes: int = 10 * 1024 * 1024  # 10 MB
    log_backup_count: int = 5
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "WatchdogConfig":
        """Load configuration from environment variables."""
        targets_raw = os.getenv("WATCHDOG_TARGETS", "")
        targets = [t.strip() for t in targets_raw.split(",") if t.strip()]
        return cls(
            targets=targets,
            max_retries=int(os.getenv("WATCHDOG_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("WATCHDOG_RETRY_DELAY", "5.0")),
            timeout=float(os.getenv("WATCHDOG_TIMEOUT", "10.0")),
            check_interval=float(os.getenv("WATCHDOG_CHECK_INTERVAL", "60.0")),
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
            slack_channel=os.getenv("SLACK_CHANNEL", "#alerts"),
            log_file=os.getenv("WATCHDOG_LOG_FILE", "watchdog.log"),
            log_max_bytes=int(os.getenv("WATCHDOG_LOG_MAX_BYTES", str(10 * 1024 * 1024))),
            log_backup_count=int(os.getenv("WATCHDOG_LOG_BACKUP_COUNT", "5")),
            log_level=os.getenv("WATCHDOG_LOG_LEVEL", "INFO"),
        )
