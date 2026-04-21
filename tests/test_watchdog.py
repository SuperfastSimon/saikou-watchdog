"""Pytest unit tests for saikou-watchdog core logic."""
import pytest
import requests

from watchdog.watchdog import (
    _check_url,
    check_with_retries,
    send_slack_alert,
    call_restart_endpoint,
    run_check_cycle,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

BASE_CFG = {
    "services": ["https://saikou.tech"],
    "timeout": 10,
    "retries": 3,
    "slack_webhook_url": "",
    "restart_endpoint": "",
    "check_interval": 300,
}


# ---------------------------------------------------------------------------
# 1. _check_url — success
# ---------------------------------------------------------------------------

def test_check_url_success(requests_mock):
    requests_mock.get("https://saikou.tech", status_code=200)
    ok, detail = _check_url("https://saikou.tech", timeout=10)
    assert ok is True
    assert "200" in detail


# ---------------------------------------------------------------------------
# 2. _check_url — non-2xx treated as failure
# ---------------------------------------------------------------------------

def test_check_url_non_200(requests_mock):
    requests_mock.get("https://saikou.tech", status_code=503)
    ok, detail = _check_url("https://saikou.tech", timeout=10)
    assert ok is False
    assert "503" in detail


# ---------------------------------------------------------------------------
# 3. _check_url — connection exception
# ---------------------------------------------------------------------------

def test_check_url_exception(requests_mock):
    requests_mock.get("https://saikou.tech", exc=requests.exceptions.ConnectionError("refused"))
    ok, detail = _check_url("https://saikou.tech", timeout=10)
    assert ok is False
    assert "refused" in detail.lower() or detail != ""


# ---------------------------------------------------------------------------
# 4. _check_url — timeout
# ---------------------------------------------------------------------------

def test_check_url_timeout(requests_mock):
    requests_mock.get("https://saikou.tech", exc=requests.exceptions.Timeout())
    ok, detail = _check_url("https://saikou.tech", timeout=10)
    assert ok is False
    assert detail == "Timeout"


# ---------------------------------------------------------------------------
# 5. check_with_retries — recovers on second attempt
# ---------------------------------------------------------------------------

def test_check_with_retries_recovers(requests_mock, monkeypatch):
    # First call fails, second succeeds
    responses = [
        {"exc": requests.exceptions.Timeout()},
        {"status_code": 200},
    ]
    requests_mock.get("https://saikou.tech", responses)

    # Skip sleep
    monkeypatch.setattr("watchdog.watchdog.time.sleep", lambda _: None)

    ok, detail, attempts = check_with_retries("https://saikou.tech", timeout=10, max_attempts=3)
    assert ok is True
    assert attempts == 2


# ---------------------------------------------------------------------------
# 6. check_with_retries — exhausts all attempts
# ---------------------------------------------------------------------------

def test_check_with_retries_exhausted(requests_mock, monkeypatch):
    requests_mock.get("https://saikou.tech", status_code=503)
    monkeypatch.setattr("watchdog.watchdog.time.sleep", lambda _: None)

    ok, detail, attempts = check_with_retries("https://saikou.tech", timeout=10, max_attempts=3)
    assert ok is False
    assert attempts == 3
    assert "503" in detail


# ---------------------------------------------------------------------------
# 7. send_slack_alert — posts JSON payload
# ---------------------------------------------------------------------------

def test_send_slack_alert_posts(requests_mock):
    webhook = "https://hooks.slack.com/services/TEST/WEBHOOK"
    requests_mock.post(webhook, status_code=200, text="ok")

    send_slack_alert(webhook, "https://saikou.tech", "HTTP 503", 3)

    assert requests_mock.called
    body = requests_mock.last_request.json()
    assert "saikou.tech" in body["text"]
    assert "503" in body["text"]


# ---------------------------------------------------------------------------
# 8. send_slack_alert — skipped when no webhook configured
# ---------------------------------------------------------------------------

def test_send_slack_alert_no_webhook(requests_mock):
    send_slack_alert("", "https://saikou.tech", "Timeout", 3)
    assert not requests_mock.called


# ---------------------------------------------------------------------------
# 9. call_restart_endpoint — posts to endpoint
# ---------------------------------------------------------------------------

def test_call_restart_endpoint(requests_mock):
    endpoint = "https://restart.example.com/restart"
    requests_mock.post(endpoint, status_code=200)

    call_restart_endpoint(endpoint, "https://saikou.tech")

    assert requests_mock.called
    body = requests_mock.last_request.json()
    assert body["service"] == "https://saikou.tech"


# ---------------------------------------------------------------------------
# 10. run_check_cycle — healthy service, no alerts
# ---------------------------------------------------------------------------

def test_run_check_cycle_all_healthy(requests_mock, monkeypatch):
    requests_mock.get("https://saikou.tech", status_code=200)
    monkeypatch.setattr("watchdog.watchdog.time.sleep", lambda _: None)

    results = run_check_cycle(BASE_CFG)
    assert results["https://saikou.tech"] is True


# ---------------------------------------------------------------------------
# 11. run_check_cycle — failing service triggers slack + restart
# ---------------------------------------------------------------------------

def test_run_check_cycle_failure_triggers_alerts(requests_mock, monkeypatch):
    webhook = "https://hooks.slack.com/services/TEST/WEBHOOK"
    restart = "https://restart.example.com/restart"

    requests_mock.get("https://saikou.tech", status_code=503)
    requests_mock.post(webhook, status_code=200, text="ok")
    requests_mock.post(restart, status_code=200)

    monkeypatch.setattr("watchdog.watchdog.time.sleep", lambda _: None)

    cfg = {**BASE_CFG, "slack_webhook_url": webhook, "restart_endpoint": restart}
    results = run_check_cycle(cfg)

    assert results["https://saikou.tech"] is False

    # Both Slack and restart endpoint must have been called
    posted_urls = [r.url for r in requests_mock.request_history if r.method == "POST"]
    assert webhook in posted_urls
    assert restart in posted_urls


# ---------------------------------------------------------------------------
# 12. run_check_cycle — multiple services, mixed results
# ---------------------------------------------------------------------------

def test_run_check_cycle_mixed(requests_mock, monkeypatch):
    requests_mock.get("https://saikou.tech", status_code=200)
    requests_mock.get("https://down.example.com", status_code=500)

    monkeypatch.setattr("watchdog.watchdog.time.sleep", lambda _: None)

    cfg = {**BASE_CFG, "services": ["https://saikou.tech", "https://down.example.com"]}
    results = run_check_cycle(cfg)

    assert results["https://saikou.tech"] is True
    assert results["https://down.example.com"] is False
