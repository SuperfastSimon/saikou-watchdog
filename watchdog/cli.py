"""CLI entrypoint: single cycle (cron) or forever loop (Render)."""
import argparse
import sys

from .config import get_config
from .watchdog import run_check_cycle, run_forever


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="watchdog",
        description="Saikou service watchdog — monitors URLs and alerts on failure.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one check cycle and exit (ideal for cron jobs).",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        default=True,
        help="Run forever (default; ideal for Render deployment).",
    )
    args = parser.parse_args()

    cfg = get_config()

    if args.once:
        results = run_check_cycle(cfg)
        any_down = any(not ok for ok in results.values())
        sys.exit(1 if any_down else 0)
    else:
        run_forever(cfg)


if __name__ == "__main__":
    main()
