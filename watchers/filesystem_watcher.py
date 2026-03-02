#!/usr/bin/env python3
"""
filesystem_watcher.py — File System Watcher for AI Employee (Bronze Tier)

Monitors the /Inbox folder for new files dropped by the user.
When a new file is detected, it:
1. Copies it to /Needs_Action/
2. Creates a metadata .md file describing the drop
3. Claude Code can then read /Needs_Action and process the items

Usage:
    python filesystem_watcher.py --vault /path/to/AI_Employee_Vault

Dependencies:
    pip install watchdog
"""

import argparse
import shutil
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileMovedEvent
except ImportError:
    print("ERROR: 'watchdog' not installed. Run: pip install watchdog")
    sys.exit(1)

from base_watcher import BaseWatcher


class DropFolderHandler(FileSystemEventHandler):
    """Handles file system events in the Inbox folder."""

    def __init__(self, vault_path: str, logger):
        self.needs_action = Path(vault_path) / 'Needs_Action'
        self.logs = Path(vault_path) / 'Logs'
        self.logger = logger
        self.processed = set()

    def on_created(self, event):
        if event.is_directory:
            return
        source = Path(event.src_path)
        # Skip hidden files, temp files, and partial writes
        name_lower = source.name.lower()
        if source.name.startswith('.'):
            return
        if '.tmp' in name_lower or name_lower.endswith('.part') or name_lower.endswith('~'):
            return
        if source in self.processed:
            return

        self.processed.add(source)
        # Small delay to let the file finish writing
        import time
        time.sleep(0.5)
        if not source.exists():
            return  # Temp file already gone
        self.logger.info(f'New file detected: {source.name}')
        self._handle_file(source)

    def on_moved(self, event):
        """Catch files created via rename (Write tool, editors, etc.)"""
        if event.is_directory:
            return
        dest = Path(event.dest_path)
        # Only care about moves INTO the inbox folder
        if dest.parent != Path(self.needs_action).parent.parent / 'Inbox':
            # Check if destination is inside our watched inbox
            pass
        name_lower = dest.name.lower()
        if dest.name.startswith('.') or '.tmp' in name_lower or name_lower.endswith('.part'):
            return
        if dest in self.processed:
            return
        self.processed.add(dest)
        self.logger.info(f'New file detected (via rename): {dest.name}')
        self._handle_file(dest)

    def on_any_event(self, event):
        """Debug: log every event to see what watchdog fires."""
        if not event.is_directory:
            self.logger.debug(f'EVENT {event.event_type}: {event.src_path}'
                              + (f' -> {event.dest_path}' if hasattr(event, 'dest_path') else ''))

    def _handle_file(self, source: Path):
        # Final guard: skip temp/partial files regardless of how we got here
        if '.tmp' in source.name.lower() or source.name.endswith(('.part', '~')):
            self.logger.debug(f'Skipping temp/partial file in _handle_file: {source.name}')
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest_name = f'FILE_{timestamp}_{source.name}'
        dest = self.needs_action / dest_name

        try:
            shutil.copy2(source, dest)
            self.logger.info(f'Copied to Needs_Action: {dest_name}')
        except FileNotFoundError:
            self.logger.warning(f'File gone before copy (temp file?): {source.name}')
            return
        except Exception as e:
            self.logger.error(f'Failed to copy {source.name}: {e}')
            return

        # Create companion metadata .md file for Claude to read
        meta_path = self.needs_action / f'FILE_{timestamp}_{source.stem}.md'
        file_size = source.stat().st_size if source.exists() else 0

        meta_content = f"""---
type: file_drop
original_name: {source.name}
copied_as: {dest_name}
size_bytes: {file_size}
received: {datetime.now().isoformat()}
priority: normal
status: pending
---

## New File Dropped for Processing

**File:** `{source.name}`
**Size:** {file_size:,} bytes
**Received:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Suggested Actions
- [ ] Review file contents
- [ ] Categorize (invoice / document / task / other)
- [ ] Take appropriate action per Company_Handbook
- [ ] Move to /Done when complete

## Notes
_Add any relevant context here._
"""
        meta_path.write_text(meta_content, encoding='utf-8')
        self.logger.info(f'Created metadata: {meta_path.name}')

        # Append to daily log
        self._log_action(source.name, dest_name)

    def _log_action(self, original: str, copied_as: str):
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs / f'{today}.json'
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": "file_drop",
            "actor": "filesystem_watcher",
            "original_file": original,
            "action_file": copied_as,
            "result": "success"
        }
        entries = []
        if log_file.exists():
            try:
                import json
                entries = json.loads(log_file.read_text(encoding='utf-8'))
            except Exception:
                entries = []
        entries.append(entry)
        import json
        log_file.write_text(json.dumps(entries, indent=2), encoding='utf-8')


class FilesystemWatcher(BaseWatcher):
    """
    Bronze Tier Watcher: Monitors the /Inbox folder for dropped files.
    Uses watchdog for real-time event detection.
    """

    def __init__(self, vault_path: str):
        super().__init__(vault_path, check_interval=5)
        self.handler = DropFolderHandler(vault_path, self.logger)
        self.observer = None

    def check_for_updates(self) -> list:
        # Handled by watchdog events, not polled
        return []

    def create_action_file(self, item) -> Path:
        # Handled by DropFolderHandler directly
        pass

    def run(self):
        self.logger.info(f'Starting FilesystemWatcher')
        self.logger.info(f'Watching inbox: {self.inbox}')
        self.logger.info(f'Action files -> {self.needs_action}')
        self.logger.info('Drop any file into the Inbox folder to trigger processing.')
        self.logger.info('Press Ctrl+C to stop.\n')

        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.inbox), recursive=False)
        self.observer.start()

        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info('Stopping watcher...')
            self.observer.stop()
        self.observer.join()
        self.logger.info('Watcher stopped.')


def main():
    parser = argparse.ArgumentParser(
        description='AI Employee - File System Watcher (Bronze Tier)'
    )
    parser.add_argument(
        '--vault',
        required=True,
        help='Absolute path to your AI_Employee_Vault folder'
    )
    args = parser.parse_args()

    vault_path = Path(args.vault).resolve()
    if not vault_path.exists():
        print(f'ERROR: Vault path does not exist: {vault_path}')
        sys.exit(1)

    watcher = FilesystemWatcher(str(vault_path))
    watcher.run()


if __name__ == '__main__':
    main()
