import logging
import time
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional, Tuple

import requests

from config import WatchdogConfig


def setup_logging(config: WatchdogConfig) -> logging.Logger:
    """Set up rotating file logger plus console handler."""
    logger = logging.getLogger("saikou_watchdog")
    logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = RotatingFileHandler(
        config.log_file,
        maxBytes=config.log_max_bytes,
        backupCount=config.log_backup_count,
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def send_slack_alert(
    webhook_url: str,
    message: str,
    channel: Optional[str] = None,
) -> bool:
    """Send an alert to Slack via incoming webhook."""
    payload: Dict = {"text": message}
    if channel:
        payload["channel"] = channel
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def check_target(
    url: str,
    config: WatchdogConfig,
    logger: logging.Logger,
) -> Tuple[bool, str]:
    """
    Check a single target URL with retries.
    Returns (success, detail_message).
    """
    last_error = ""
    for attempt in range(1, config.max_retries + 1):
        try:
            resp = requests.get(url, timeout=config.timeout)
            if resp.status_code < 400:
                logger.info(f"[OK] {url} -> {resp.status_code} (attempt {attempt})")
                return True, f"HTTP {resp.status_code}"
            last_error = f"HTTP {resp.status_code}"
        except requests.Timeout:
            last_error = f"Timeout after {config.timeout}s"
        except requests.ConnectionError as exc:
            last_error = f"Connection error: {exc}"
        except requests.RequestException as exc:
            last_error = f"Request error: {exc}"

        logger.warning(f"[FAIL] {url} attempt {attempt}/{config.max_retries} - {last_error}")
        if attempt < config.max_retries:
            time.sleep(config.retry_delay)

    return False, last_error


def run_watchdog(config: WatchdogConfig, logger: logging.Logger) -> None:
    """Main watchdog loop - checks all targets on each interval."""
    logger.info(
        f"Saikou Watchdog started. Monitoring {len(config.targets)} target(s) "
        f"every {config.check_interval}s."
    )
    while True:
        for url in config.targets:
            success, detail = check_target(url, config, logger)
            if not success:
                alert_msg = (
                    f":rotating_light: *Saikou Watchdog Alert*\n"
                    f"Target DOWN: `{url}`\n"
                    f"Reason: {detail}\n"
                    f"Retries exhausted: {config.max_retries}"
                )
                logger.error(f"[DOWN] {url} - {detail}")
                if config.slack_webhook_url:
                    sent = send_slack_alert(
                        config.slack_webhook_url,
                        alert_msg,
                        config.slack_channel,
                    )
                    logger.info("Slack alert sent." if sent else "Failed to send Slack alert.")
        time.sleep(config.check_interval)
