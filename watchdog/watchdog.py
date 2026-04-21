"""Core watchdog logic: check, retry, alert, restart."""
import logging
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

import requests

from .config import get_config

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logger(name: str = "watchdog") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # Rotating file: 5 MB × 3 backups
    fh = RotatingFileHandler("watchdog.log", maxBytes=5 * 1024 * 1024, backupCount=3)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


logger = setup_logger()

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _check_url(url: str, timeout: int) -> tuple[bool, str]:
    """
    Returns (ok, detail).
    ok=True  → HTTP 200-299
    ok=False → non-2xx or exception
    """
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.ok:
            return True, f"HTTP {resp.status_code}"
        return False, f"HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.RequestException as exc:
        return False, str(exc)


def check_with_retries(url: str, timeout: int, max_attempts: int, backoff_base: float = 5.0) -> tuple[bool, str, int]:
    """
    Attempt up to `max_attempts` times with exponential backoff.
    Returns (recovered, last_detail, attempts_made).
    Behavior: attempt 1 (initial), then retries 2..max_attempts.
    """
    last_detail = ""
    for attempt in range(1, max_attempts + 1):
        ok, detail = _check_url(url, timeout)
        last_detail = detail
        if ok:
            if attempt > 1:
                logger.info("  [%s] recovered on attempt %d: %s", url, attempt, detail)
            return True, detail, attempt
        logger.warning("  [%s] attempt %d/%d failed: %s", url, attempt, max_attempts, detail)
        if attempt < max_attempts:
            sleep_s = backoff_base * (2 ** (attempt - 1))  # 5s, 10s, 20s …
            logger.info("  Retrying in %.0fs …", sleep_s)
            time.sleep(sleep_s)

    return False, last_detail, max_attempts


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def send_slack_alert(webhook_url: str, service_url: str, detail: str, attempts: int) -> None:
    if not webhook_url:
        return
    ts = datetime.now(timezone.utc).isoformat()
    payload = {
        "text": (
            f":red_circle: *Watchdog Alert* — service is DOWN\n"
            f"• *URL:* {service_url}\n"
            f"• *Reason:* {detail}\n"
            f"• *Attempts:* {attempts}\n"
            f"• *Time (UTC):* {ts}"
        )
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.ok:
            logger.info("  Slack alert sent for %s", service_url)
        else:
            logger.error("  Slack alert failed: HTTP %s", resp.status_code)
    except requests.exceptions.RequestException as exc:
        logger.error("  Slack alert error: %s", exc)


def call_restart_endpoint(endpoint: str, service_url: str) -> None:
    if not endpoint:
        return
    try:
        resp = requests.post(endpoint, json={"service": service_url}, timeout=10)
        logger.info("  Restart endpoint called → HTTP %s", resp.status_code)
    except requests.exceptions.RequestException as exc:
        logger.error("  Restart endpoint error: %s", exc)


# ---------------------------------------------------------------------------
# One check cycle
# ---------------------------------------------------------------------------

def run_check_cycle(cfg: dict | None = None) -> dict[str, bool]:
    """
    Check every service once (with retries).
    Returns {url: ok_bool} for all services.
    """
    if cfg is None:
        cfg = get_config()

    results: dict[str, bool] = {}

    for url in cfg["services"]:
        logger.info("Checking %s …", url)
        ok, detail, attempts = check_with_retries(
            url,
            timeout=cfg["timeout"],
            max_attempts=cfg["retries"],
        )
        results[url] = ok

        if ok:
            logger.info("  [OK] %s — %s", url, detail)
        else:
            logger.error("  [DOWN] %s — %s (after %d attempt(s))", url, detail, attempts)

            # 1. Trigger restart endpoint once per failure sequence
            call_restart_endpoint(cfg["restart_endpoint"], url)

            # 2. Send Slack alert
            send_slack_alert(cfg["slack_webhook_url"], url, detail, attempts)

    return results


# ---------------------------------------------------------------------------
# Forever loop
# ---------------------------------------------------------------------------

def run_forever(cfg: dict | None = None) -> None:
    """Run check cycles indefinitely (Render long-running process)."""
    if cfg is None:
        cfg = get_config()

    logger.info("Watchdog started. Interval=%ss, Services=%s", cfg["check_interval"], cfg["services"])
    while True:
        run_check_cycle(cfg)
        logger.info("Next check in %ss …", cfg["check_interval"])
        time.sleep(cfg["check_interval"])
