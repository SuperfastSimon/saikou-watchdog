# Saikou Watchdog

Production-ready service health monitor for the Saikou.tech platform.

## Features

- **Multi-target monitoring** - watch any number of URLs
- **Configurable retries** - with delay between attempts
- **Slack alerts** - instant notifications when a service goes down
- **Rotating logs** - disk-safe rotating file logs (configurable size + backups)
- **CLI interface** - run from terminal with full argument support
- **Environment-driven config** - 12-factor app compatible

## Quick Start

```bash
pip install -r requirements.txt

python cli.py https://saikou.tech https://api.saikou.tech \
  --slack-webhook https://hooks.slack.com/YOUR_WEBHOOK \
  --interval 30 \
  --retries 3
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `WATCHDOG_TARGETS` | - | Comma-separated URLs to monitor |
| `WATCHDOG_MAX_RETRIES` | `3` | Retries before marking down |
| `WATCHDOG_RETRY_DELAY` | `5.0` | Seconds between retries |
| `WATCHDOG_TIMEOUT` | `10.0` | Request timeout (seconds) |
| `WATCHDOG_CHECK_INTERVAL` | `60.0` | Seconds between check cycles |
| `SLACK_WEBHOOK_URL` | - | Slack incoming webhook URL |
| `SLACK_CHANNEL` | `#alerts` | Slack channel name |
| `WATCHDOG_LOG_FILE` | `watchdog.log` | Log file path |
| `WATCHDOG_LOG_MAX_BYTES` | `10485760` | Max log file size (bytes) |
| `WATCHDOG_LOG_BACKUP_COUNT` | `5` | Number of rotated log backups |
| `WATCHDOG_LOG_LEVEL` | `INFO` | Logging level |

## Running Tests

```bash
pytest tests/ -v
```

## Package Structure

```
saikou-watchdog/
|-- config.py
|-- watchdog.py
|-- cli.py
|-- tests/
|   |-- __init__.py
|   +-- test_watchdog.py
|-- requirements.txt
|-- setup.py
+-- README.md
```

## Genesis Protocol Integration

This watchdog is a component of the **Genesis Protocol Maintainer Agent**.
It can be triggered by the Boss Agent to health-check deployed services
and report back via Slack or log files.
