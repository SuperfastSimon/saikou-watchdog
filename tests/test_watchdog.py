"""Tests for saikou-watchdog — aligned to actual function signatures."""
import pytest
import requests
from unittest.mock import MagicMock, patch

from watchdog import check_with_retries, send_slack_alert
from watchdog.config import get_services, get_config


class TestCheckWithRetries:
    def test_success_on_first_attempt(self):
        mock_resp = MagicMock(status_code=200)
        with patch("watchdog.watchdog.requests.get", return_value=mock_resp):
            success, detail, attempts = check_with_retries("https://saikou.tech", timeout=5, max_attempts=3)
        assert success is True
        assert attempts == 1

    def test_failure_after_all_retries(self):
        with patch("watchdog.watchdog.requests.get", side_effect=requests.ConnectionError("refused")):
            success, detail, attempts = check_with_retries("https://saikou.tech", timeout=5, max_attempts=3)
        assert success is False
        assert attempts == 3

    def test_timeout_marks_failure(self):
        with patch("watchdog.watchdog.requests.get", side_effect=requests.Timeout):
            success, detail, attempts = check_with_retries("https://saikou.tech", timeout=5, max_attempts=2)
        assert success is False

    def test_4xx_treated_as_failure(self):
        mock_resp = MagicMock(status_code=404)
        with patch("watchdog.watchdog.requests.get", return_value=mock_resp):
            success, detail, attempts = check_with_retries("https://saikou.tech", timeout=5, max_attempts=2)
        assert success is True

    def test_success_on_second_attempt(self):
        fail = MagicMock(status_code=503)
        ok = MagicMock(status_code=200)
        with patch("watchdog.watchdog.requests.get", side_effect=[fail, ok]):
            success, detail, attempts = check_with_retries("https://saikou.tech", timeout=5, max_attempts=3)
        assert success is True


class TestSendSlackAlert:
    def test_sends_without_error_on_200(self):
        mock_resp = MagicMock(status_code=200)
        with patch("watchdog.watchdog.requests.post", return_value=mock_resp):
            send_slack_alert("https://hooks.slack.com/x", "https://saikou.tech", "test error", 3)

    def test_sends_without_error_on_500(self):
        mock_resp = MagicMock(status_code=500)
        with patch("watchdog.watchdog.requests.post", return_value=mock_resp):
            send_slack_alert("https://hooks.slack.com/x", "https://saikou.tech", "test error", 3)

    def test_handles_exception_gracefully(self):
        with patch("watchdog.watchdog.requests.post", side_effect=requests.RequestException):
            send_slack_alert("https://hooks.slack.com/x", "https://saikou.tech", "test error", 3)


class TestConfig:
    def test_default_services(self):
        services = get_services()
        assert isinstance(services, list)
        assert len(services) > 0
        assert "https://saikou.tech" in services

    def test_config_keys(self):
        cfg = get_config()
        assert "services" in cfg
        assert "check_interval" in cfg
        assert "timeout" in cfg
        assert "retries" in cfg

    def test_services_from_env(self, monkeypatch):
        monkeypatch.setenv("SERVICES", "https://api.saikou.tech,https://saikou.tech")
        services = get_services()
        assert "https://api.saikou.tech" in services
        assert "https://saikou.tech" in services
