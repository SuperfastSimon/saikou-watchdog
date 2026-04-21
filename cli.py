"""Command-line interface for Saikou Watchdog."""
import argparse
import sys

from config import WatchdogConfig
from watchdog import run_watchdog, setup_logging


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="saikou-watchdog",
        description="Production-grade service health monitor with Slack alerts.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="URLs to monitor (overrides WATCHDOG_TARGETS env var).",
    )
    parser.add_argument("--interval", type=float, default=None, help="Seconds between checks.")
    parser.add_argument("--retries", type=int, default=None, help="Max retries per target.")
    parser.add_argument("--slack-webhook", default=None, help="Slack incoming webhook URL.")
    parser.add_argument("--log-file", default=None, help="Path to rotating log file.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    config = WatchdogConfig.from_env()

    if args.targets:
        config.targets = args.targets
    if args.interval is not None:
        config.check_interval = args.interval
    if args.retries is not None:
        config.max_retries = args.retries
    if args.slack_webhook:
        config.slack_webhook_url = args.slack_webhook
    if args.log_file:
        config.log_file = args.log_file

    if not config.targets:
        print(
            "Error: No targets specified. Use positional args or WATCHDOG_TARGETS env var.",
            file=sys.stderr,
        )
        sys.exit(1)

    logger = setup_logging(config)
    run_watchdog(config, logger)


if __name__ == "__main__":
    main()
