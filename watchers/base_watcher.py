# base_watcher.py - Template for all watchers (Gold Tier: error recovery + graceful degradation)
import time
import logging
import sys
import json
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

MAX_CONSECUTIVE_ERRORS = 5   # Disable watcher after this many back-to-back failures
RETRY_BACKOFF = [5, 15, 30, 60, 120]  # Seconds to wait between retries


class BaseWatcher(ABC):
    def __init__(self, vault_path: str, check_interval: int = 60):
        self.vault_path = Path(vault_path)
        self.inbox = self.vault_path / 'Inbox'
        self.needs_action = self.vault_path / 'Needs_Action'
        self.done = self.vault_path / 'Done'
        self.logs = self.vault_path / 'Logs'
        self.check_interval = check_interval
        self.logger = logging.getLogger(self.__class__.__name__)
        self._consecutive_errors = 0
        self._total_errors = 0
        self._total_items_processed = 0

        # Ensure required folders exist
        for folder in [self.inbox, self.needs_action, self.done, self.logs]:
            folder.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def check_for_updates(self) -> list:
        """Return list of new items to process"""
        pass

    @abstractmethod
    def create_action_file(self, item) -> Path:
        """Create .md file in Needs_Action folder"""
        pass

    def on_error(self, error: Exception):
        """Override in subclass for custom error handling (e.g. restart browser)."""
        pass

    def log_error(self, error: Exception, context: str = ""):
        """Write error to vault log file for audit trail."""
        try:
            log_file = self.logs / f"{datetime.now().strftime('%Y-%m-%d')}.json"
            entries = json.loads(log_file.read_text(encoding='utf-8')) if log_file.exists() else []
            entries.append({
                "timestamp": datetime.now().isoformat(),
                "action_type": "watcher_error",
                "actor": self.__class__.__name__,
                "target": context or "check_for_updates",
                "parameters": {"error": str(error)},
                "approval_status": "auto",
                "approved_by": "system",
                "result": "failure",
            })
            log_file.write_text(json.dumps(entries, indent=2), encoding='utf-8')
        except Exception:
            pass  # Don't let logging errors crash the watcher

    def run(self):
        self.logger.info(f'Starting {self.__class__.__name__}')
        self.logger.info(f'Vault path: {self.vault_path}')
        self.logger.info(f'Check interval: {self.check_interval}s')
        while True:
            try:
                items = self.check_for_updates()
                if items:
                    self.logger.info(f'Found {len(items)} new item(s)')
                for item in items:
                    action_file = self.create_action_file(item)
                    self.logger.info(f'Created action file: {action_file}')
                    self._total_items_processed += 1
                # Reset error counter on success
                self._consecutive_errors = 0

            except KeyboardInterrupt:
                self.logger.info('Watcher stopped by user')
                break

            except Exception as e:
                self._consecutive_errors += 1
                self._total_errors += 1
                backoff = RETRY_BACKOFF[min(self._consecutive_errors - 1, len(RETRY_BACKOFF) - 1)]

                self.logger.error(f'Error ({self._consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {e}', exc_info=True)
                self.log_error(e)
                self.on_error(e)

                # Graceful degradation: disable after too many failures
                if self._consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    self.logger.error(
                        f'{self.__class__.__name__} disabled after {MAX_CONSECUTIVE_ERRORS} consecutive errors. '
                        f'Fix the issue and restart.'
                    )
                    self._write_alert(f"Watcher disabled after {MAX_CONSECUTIVE_ERRORS} crashes")
                    break

                self.logger.info(f'Retrying in {backoff}s...')
                time.sleep(backoff)
                continue

            time.sleep(self.check_interval)

    def _write_alert(self, message: str):
        """Write a system alert to /Needs_Action/ for the AI Employee to process."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            alert_file = self.needs_action / f'ALERT_{self.__class__.__name__.upper()}_{timestamp}.md'
            alert_file.write_text(
                f"---\ntype: system_alert\nsource: {self.__class__.__name__}\n"
                f"severity: high\ncreated: {datetime.now().isoformat()}\nstatus: pending\n---\n\n"
                f"## System Alert\n\n**Message:** {message}\n"
                f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"## Action Required\n- [ ] Review error logs in /Logs/\n"
                f"- [ ] Check watcher configuration\n- [ ] Restart watcher if needed\n",
                encoding='utf-8'
            )
            self.logger.info(f'Alert written: {alert_file.name}')
        except Exception:
            pass
