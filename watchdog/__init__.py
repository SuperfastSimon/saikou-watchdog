__version__ = "1.0.0"
from watchdog.watchdog import setup_logger, check_with_retries, send_slack_alert, call_restart_endpoint, run_check_cycle, run_forever
check_target = check_with_retries

def setup_logging(config_or_name="watchdog"):
    """Accept either a config object or a string name."""
    if isinstance(config_or_name, str):
        return setup_logger(config_or_name)
    return setup_logger("watchdog")
