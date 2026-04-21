# Saikou Watchdog

Production-ready service health monitor for [saikou.tech](https://saikou.tech).  
Checks URLs on a schedule, retries on failure, triggers restarts, and fires Slack alerts.  
Deployable as a Render long-running process or a cron job.

---

## File Tree

```
saikou-watchdog/
├── watchdog/
│   ├── __init__.py
│   ├── config.py        # Env-var configuration
│   ├── watchdog.py      # Core logic: check, retry, alert, restart
│   └── cli.py           # Argparse entrypoint
├── tests/
│   └── test_watchdog.py # 12 pytest unit tests
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Environment Variables

| Variable           | Default                  | Description                                      |
|--------------------|--------------------------|--------------------------------------------------|
| `SERVICES`         | `https://saikou.tech`    | Comma-separated URLs to monitor                  |
| `CHECK_INTERVAL`   | `300`                    | Seconds between check cycles (loop mode)         |
| `TIMEOUT`          | `10`                     | HTTP request timeout in seconds                  |
| `RETRIES`          | `3`                      | Total attempts per service (1 initial + retries) |
| `SLACK_WEBHOOK_URL`| *(empty — disabled)*     | Slack Incoming Webhook URL for alerts            |
| `RESTART_ENDPOINT` | *(empty — disabled)*     | POST endpoint called on failure (e.g. Render deploy hook) |

---

## Retry Behaviour

- Attempt 1 → wait 5s → Attempt 2 → wait 10s → Attempt 3
- Exponential backoff: `5 × 2^(attempt-1)` seconds
- If all attempts fail: call `RESTART_ENDPOINT` (once) then send Slack alert

---

## Setup

```bash
git clone https://github.com/SuperfastSimon/saikou-watchdog
cd saikou-watchdog
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Copy and edit your environment:

```bash
cp .env.example .env   # or export vars directly
```

---

## Usage

### Run once (cron mode)

```bash
python -m watchdog.cli --once
```

Exit code `0` = all healthy, `1` = one or more services down.

**Crontab example** (every 5 minutes):

```cron
*/5 * * * * cd /opt/saikou-watchdog && /opt/saikou-watchdog/.venv/bin/python -m watchdog.cli --once >> /var/log/watchdog-cron.log 2>&1
```

### Run forever (Render / Docker)

```bash
python -m watchdog.cli
```

or explicitly:

```bash
python -m watchdog.cli --loop
```

---

## Render Deployment

1. Create a new **Background Worker** service on Render.
2. Set **Build Command**: `pip install -r requirements.txt`
3. Set **Start Command**: `python -m watchdog.cli`
4. Add environment variables in the Render dashboard.

That's it — Render keeps the process alive and restarts it on crash.

**Render deploy hook as RESTART_ENDPOINT:**  
Grab your service's deploy hook URL from Render → Settings → Deploy Hook,  
then set `RESTART_ENDPOINT=https://api.render.com/deploy/srv-XXXX?key=YYYY`.

---

## Running Tests

```bash
pytest tests/ -v
```

Expected output:

```
tests/test_watchdog.py::test_check_url_success PASSED
tests/test_watchdog.py::test_check_url_non_200 PASSED
tests/test_watchdog.py::test_check_url_exception PASSED
tests/test_watchdog.py::test_check_url_timeout PASSED
tests/test_watchdog.py::test_check_with_retries_recovers PASSED
tests/test_watchdog.py::test_check_with_retries_exhausted PASSED
tests/test_watchdog.py::test_send_slack_alert_posts PASSED
tests/test_watchdog.py::test_send_slack_alert_no_webhook PASSED
tests/test_watchdog.py::test_call_restart_endpoint PASSED
tests/test_watchdog.py::test_run_check_cycle_all_healthy PASSED
tests/test_watchdog.py::test_run_check_cycle_failure_triggers_alerts PASSED
tests/test_watchdog.py::test_run_check_cycle_mixed PASSED

12 passed in 0.XXs
```

---

## Slack Alert Format

```
🔴 Watchdog Alert — service is DOWN
• URL: https://saikou.tech
• Reason: HTTP 503
• Attempts: 3
• Time (UTC): 2026-04-21T10:00:00+00:00
```

---

## Log Output (watchdog.log)

Rotating log, 5 MB × 3 backups. Sample:

```
2026-04-21 10:00:00,123 [INFO] Checking https://saikou.tech …
2026-04-21 10:00:01,456 [INFO]   [OK] https://saikou.tech — HTTP 200
2026-04-21 10:05:00,789 [INFO] Checking https://saikou.tech …
2026-04-21 10:05:11,012 [WARNING]   attempt 1/3 failed: Timeout
2026-04-21 10:05:11,013 [INFO]   Retrying in 5s …
2026-04-21 10:05:16,500 [WARNING]   attempt 2/3 failed: Timeout
2026-04-21 10:05:16,501 [INFO]   Retrying in 10s …
2026-04-21 10:05:27,200 [WARNING]   attempt 3/3 failed: Timeout
2026-04-21 10:05:27,201 [ERROR]   [DOWN] https://saikou.tech — Timeout (after 3 attempt(s))
2026-04-21 10:05:27,202 [INFO]   Restart endpoint called → HTTP 200
2026-04-21 10:05:27,400 [INFO]   Slack alert sent for https://saikou.tech
```
