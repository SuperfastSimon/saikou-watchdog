"""Configuration loaded from environment variables."""
import os

def get_services() -> list[str]:
    raw = os.getenv("SERVICES", "https://saikou.tech")
    return [s.strip() for s in raw.split(",") if s.strip()]

def get_config() -> dict:
    return {
        "services": get_services(),
        "check_interval": int(os.getenv("CHECK_INTERVAL", "300")),
        "timeout": int(os.getenv("TIMEOUT", "10")),
        "retries": int(os.getenv("RETRIES", "3")),
        "slack_webhook_url": os.getenv("SLACK_WEBHOOK_URL", ""),
        "restart_endpoint": os.getenv("RESTART_ENDPOINT", ""),
    }
