"""Pytest tests for Saikou Watchdog."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from config import WatchdogConfig
from watchdog import check_target, send_slack_alert, setup_logging


@pytest.fixture
def config(tmp_path):
    return WatchdogConfig(
        targets=["https://saikou.tech"],
        max_retries=2,
        retry_delay=0.0,
        timeout=5.0,
        slack_webhook_url="https://hooks.slack.com/test",
        slack_channel="#test",
        log_file=str(tmp_path / "test.log"),
    )


@pytest.fixture
def logger(config):
    return setup_logging(config)


class TestCheckTarget:
    def test_success_on_first_attempt(self, config, logger):
        mock_resp = MagicMock(status_code=200)
        with patch("watchdog.requests.get", return_value=mock_resp):
            success, detail = check_target("https://saikou.tech", config, logger)
        assert success is True
        assert "200" in detail

    def test_failure_after_all_retries(self, config, logger):
        with patch("watchdog.requests.get", side_effect=requests.ConnectionError("refused")):
            success, detail = check_target("https://saikou.tech", config, logger)
        assert success is False
        assert "Connection error" in detail

    def test_timeout_marks_failure(self, config, logger):
        with patch("watchdog.requests.get", side_effect=requests.Timeout):
            success, detail = check_target("https://saikou.tech", config, logger)
        assert success is False
        assert "Timeout" in detail

    def test_4xx_treated_as_failure(self, config, logger):
        mock_resp = MagicMock(status_code=404)
        with patch("watchdog.requests.get", return_value=mock_resp):
            success, detail = check_target("https://saikou.tech", config, logger)
        assert success is False

    def test_success_on_second_attempt(self, config, logger):
        fail = MagicMock(status_code=503)
        ok = MagicMock(status_code=200)
        with patch("watchdog.requests.get", side_effect=[fail, ok]):
            success, detail = check_target("https://saikou.tech", config, logger)
        assert success is True


class TestSendSlackAlert:
    def test_returns_true_on_200(self):
        mock_resp = MagicMock(status_code=200)
        with patch("watchdog.requests.post", return_value=mock_resp):
            assert send_slack_alert("https://hooks.slack.com/x", "msg") is True

    def test_returns_false_on_non_200(self):
        mock_resp = MagicMock(status_code=500)
        with patch("watchdog.requests.post", return_value=mock_resp):
            assert send_slack_alert("https://hooks.slack.com/x", "msg") is False

    def test_returns_false_on_exception(self):
        with patch("watchdog.requests.post", side_effect=requests.RequestException):
            assert send_slack_alert("https://hooks.slack.com/x", "msg") is False


class TestWatchdogConfig:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("WATCHDOG_TARGETS", "https://saikou.tech,https://api.saikou.tech")
        monkeypatch.setenv("WATCHDOG_MAX_RETRIES", "5")
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/xyz")
        config = WatchdogConfig.from_env()
        assert len(config.targets) == 2
        assert config.max_retries == 5
        assert config.slack_webhook_url == "https://hooks.slack.com/xyz"

    def test_defaults(self):
        config = WatchdogConfig()
        assert config.max_retries == 3
        assert config.check_interval == 60.0
        assert config.log_backup_count == 5
