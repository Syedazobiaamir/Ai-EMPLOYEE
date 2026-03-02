#!/usr/bin/env python3
"""
orchestrator.py — Master Orchestrator for AI Employee (Silver Tier)

The Orchestrator is the heartbeat of the AI Employee system. It:
1. Starts and monitors all Watcher processes (Gmail, WhatsApp, LinkedIn, FileSystem)
2. Watches /Approved folder — when human moves a file there, triggers Claude to act
3. Runs scheduled tasks (Daily Briefing at 8am, LinkedIn post generation, Weekly Audit)
4. Implements the Watchdog pattern — auto-restarts crashed watchers
5. Provides graceful shutdown with SIGINT/SIGTERM

Usage:
    python orchestrator.py --vault ./AI_Employee_Vault
    python orchestrator.py --vault ./AI_Employee_Vault --dry-run
    python orchestrator.py --vault ./AI_Employee_Vault --no-gmail
    python orchestrator.py --vault ./AI_Employee_Vault --no-whatsapp

Architecture:
    Orchestrator
    ├── FilesystemWatcher (subprocess)
    ├── GmailWatcher (subprocess)
    ├── WhatsAppWatcher (subprocess)
    ├── LinkedInWatcher (subprocess)
    ├── ApprovalWatcher (internal thread)
    └── Scheduler (internal thread)
"""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, time as dt_time
from pathlib import Path

# ─── Logging Setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger('Orchestrator')

# ─── Config ───────────────────────────────────────────────────────────────────

PYTHON = sys.executable  # Use the same Python as orchestrator

# Scheduled task times (24-hour format)
DAILY_BRIEFING_TIME = dt_time(8, 0)    # 8:00 AM
LINKEDIN_POST_TIME = dt_time(9, 0)     # 9:00 AM
WEEKLY_AUDIT_DAY = 0                   # Monday (0=Mon, 6=Sun)
WEEKLY_AUDIT_TIME = dt_time(7, 30)     # 7:30 AM Monday

# Watcher restart delay on crash
RESTART_DELAY = 30  # seconds

# Max consecutive crashes before alerting
MAX_CRASHES = 5


class WatcherProcess:
    """Manages a single watcher subprocess with auto-restart."""

    def __init__(self, name: str, command: list, vault_path: Path, enabled: bool = True):
        self.name = name
        self.command = command
        self.vault_path = vault_path
        self.enabled = enabled
        self.process: subprocess.Popen = None
        self.crash_count = 0
        self.started_at: datetime = None
        self.logger = logging.getLogger(f'Orchestrator.{name}')

    def start(self):
        if not self.enabled:
            self.logger.info(f'{self.name} is disabled, skipping')
            return
        self.logger.info(f'Starting {self.name}...')
        try:
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            self.started_at = datetime.now()
            self.logger.info(f'{self.name} started (PID: {self.process.pid})')
        except Exception as e:
            self.logger.error(f'Failed to start {self.name}: {e}')

    def is_running(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def stop(self):
        if self.process and self.is_running():
            self.logger.info(f'Stopping {self.name} (PID: {self.process.pid})...')
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def check_and_restart(self):
        """Check if watcher is running; restart if crashed."""
        if not self.enabled:
            return
        if not self.is_running():
            exit_code = self.process.returncode if self.process else None
            self.crash_count += 1

            if self.crash_count > MAX_CRASHES:
                self.logger.error(
                    f'{self.name} has crashed {self.crash_count} times. '
                    f'Disabling auto-restart. Check logs!'
                )
                self._write_alert(f'{self.name} disabled after {self.crash_count} crashes')
                self.enabled = False
                return

            self.logger.warning(
                f'{self.name} is not running (exit: {exit_code}). '
                f'Restarting in {RESTART_DELAY}s... (crash #{self.crash_count})'
            )
            time.sleep(RESTART_DELAY)
            self.start()

    def _write_alert(self, message: str):
        """Write a system alert to /Needs_Action."""
        needs_action = self.vault_path / 'Needs_Action'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        alert_file = needs_action / f'ALERT_ORCHESTRATOR_{timestamp}.md'
        try:
            alert_file.write_text(
                f"""---
type: system_alert
source: orchestrator
severity: high
created: {datetime.now().isoformat()}
status: pending
---

## System Alert

**Message:** {message}
**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Action Required
- [ ] Review orchestrator logs
- [ ] Check watcher health
- [ ] Restart services if needed
""", encoding='utf-8'
            )
        except Exception as e:
            self.logger.error(f'Could not write alert: {e}')


class ApprovalWatcher:
    """
    Watches /Approved folder for files moved there by the human.
    When a file appears, triggers the appropriate action via Claude.
    """

    def __init__(self, vault_path: Path, dry_run: bool = False):
        self.vault_path = vault_path
        self.approved_dir = vault_path / 'Approved'
        self.done_dir = vault_path / 'Done'
        self.dry_run = dry_run
        self.processed: set = set()
        self.logger = logging.getLogger('Orchestrator.ApprovalWatcher')
        self._stop_event = threading.Event()

    def _process_approval(self, approval_file: Path):
        """Process an approved file and execute the corresponding action."""
        try:
            content = approval_file.read_text(encoding='utf-8')
            # Parse YAML frontmatter
            action_type = ''
            for line in content.split('\n'):
                if line.startswith('action:'):
                    action_type = line.split(':', 1)[1].strip()
                    break

            self.logger.info(f'Processing approval: {approval_file.name} (action: {action_type})')

            if self.dry_run:
                self.logger.info(f'[DRY RUN] Would execute: {action_type} for {approval_file.name}')
                self._log_execution(approval_file.name, action_type, 'dry_run')
                self._move_to_done(approval_file)
                return

            # Route to appropriate handler
            if 'linkedin_post' in approval_file.name.lower() or action_type == 'post_to_linkedin':
                self._handle_linkedin_post(approval_file)
            elif action_type in ('send_email', 'email_send'):
                self._handle_email_send(approval_file)
            elif action_type == 'payment':
                self._handle_payment(approval_file)
            else:
                # Generic: log and move to done
                self.logger.info(f'Generic approval processed: {approval_file.name}')
                self._log_execution(approval_file.name, action_type, 'acknowledged')
                self._move_to_done(approval_file)

        except Exception as e:
            self.logger.error(f'Error processing approval {approval_file.name}: {e}')

    def _handle_linkedin_post(self, approval_file: Path):
        """Execute approved LinkedIn post."""
        self.logger.info(f'Executing LinkedIn post: {approval_file.name}')
        try:
            result = subprocess.run(
                [PYTHON,
                 str(Path(__file__).parent / 'watchers' / 'linkedin_watcher.py'),
                 '--vault', str(self.vault_path),
                 '--post-approved'],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                self.logger.info('LinkedIn post published successfully')
                self._log_execution(approval_file.name, 'linkedin_post', 'success')
            else:
                self.logger.error(f'LinkedIn post failed: {result.stderr}')
                self._log_execution(approval_file.name, 'linkedin_post', f'error: {result.stderr[:200]}')
        except Exception as e:
            self.logger.error(f'LinkedIn post error: {e}')
        self._move_to_done(approval_file)

    def _handle_email_send(self, approval_file: Path):
        """Log email send approval — Claude handles via MCP."""
        self.logger.info(f'Email send approved: {approval_file.name}')
        self.logger.info('Email will be sent by Claude Code via Email MCP server')
        self._log_execution(approval_file.name, 'send_email', 'approved_for_mcp')
        # Don't move to Done yet — Claude will move it after sending via MCP

    def _handle_payment(self, approval_file: Path):
        """Log payment approval — NEVER auto-execute payments."""
        self.logger.info(f'Payment approval noted: {approval_file.name}')
        self.logger.warning('PAYMENT actions require manual execution. Logging only.')
        self._log_execution(approval_file.name, 'payment', 'approved_manual_execution_required')
        # Leave in /Approved for human to execute manually

    def _move_to_done(self, approval_file: Path):
        self.done_dir.mkdir(exist_ok=True)
        dest = self.done_dir / approval_file.name
        approval_file.rename(dest)
        self.logger.info(f'Moved {approval_file.name} to /Done')

    def _log_execution(self, filename: str, action_type: str, result: str):
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.vault_path / 'Logs' / f'{today}.json'
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": "orchestrator",
            "target": filename,
            "parameters": {},
            "approval_status": "approved",
            "approved_by": "human",
            "result": result,
            "dry_run": self.dry_run
        }
        entries = []
        if log_file.exists():
            try:
                entries = json.loads(log_file.read_text(encoding='utf-8'))
            except Exception:
                entries = []
        entries.append(entry)
        log_file.write_text(json.dumps(entries, indent=2), encoding='utf-8')

    def run(self):
        """Watch /Approved folder in a loop."""
        self.logger.info(f'ApprovalWatcher watching: {self.approved_dir}')
        self.approved_dir.mkdir(exist_ok=True)

        while not self._stop_event.is_set():
            try:
                for md_file in self.approved_dir.glob('*.md'):
                    if md_file.name not in self.processed:
                        self.processed.add(md_file.name)
                        self._process_approval(md_file)
            except Exception as e:
                self.logger.error(f'ApprovalWatcher error: {e}')
            time.sleep(10)  # Poll every 10 seconds

    def stop(self):
        self._stop_event.set()


class Scheduler:
    """Runs scheduled tasks at configured times."""

    def __init__(self, vault_path: Path, dry_run: bool = False):
        self.vault_path = vault_path
        self.dry_run = dry_run
        self.logger = logging.getLogger('Orchestrator.Scheduler')
        self._stop_event = threading.Event()
        self._last_run: dict = {}  # task_name -> date

    def _should_run_daily(self, task_name: str, run_time: dt_time) -> bool:
        now = datetime.now()
        today = now.date().isoformat()
        last = self._last_run.get(task_name)
        if last == today:
            return False
        current_time = now.time()
        return current_time >= run_time

    def _should_run_weekly(self, task_name: str, weekday: int, run_time: dt_time) -> bool:
        now = datetime.now()
        week_key = f"{now.isocalendar()[1]}_{now.year}"  # week number + year
        last = self._last_run.get(task_name)
        if last == week_key:
            return False
        return now.weekday() == weekday and now.time() >= run_time

    def _run_task(self, task_name: str, description: str):
        """Write a scheduled task trigger to /Needs_Action."""
        self.logger.info(f'Scheduled task triggered: {task_name}')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'SCHEDULED_{task_name.upper()}_{timestamp}.md'
        filepath = self.vault_path / 'Needs_Action' / filename

        content = f"""---
type: scheduled_task
task_name: {task_name}
triggered_by: orchestrator_scheduler
triggered_at: {datetime.now().isoformat()}
status: pending
dry_run: {str(self.dry_run).lower()}
---

## Scheduled Task: {task_name.replace('_', ' ').title()}

**Description:** {description}
**Triggered:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Action Required
Run `/{task_name.replace('_', '-')}` to execute this scheduled task.
"""
        if not self.dry_run:
            filepath.write_text(content, encoding='utf-8')
            self.logger.info(f'Created scheduled task file: {filename}')
        else:
            self.logger.info(f'[DRY RUN] Would create: {filename}')

    def run(self):
        """Check scheduled tasks every minute."""
        self.logger.info('Scheduler started')
        self.logger.info(f'Daily briefing at: {DAILY_BRIEFING_TIME}')
        self.logger.info(f'LinkedIn post at: {LINKEDIN_POST_TIME}')
        self.logger.info(f'Weekly audit on Monday at: {WEEKLY_AUDIT_TIME}')

        while not self._stop_event.is_set():
            try:
                # Daily briefing at 8:00 AM
                if self._should_run_daily('daily_briefing', DAILY_BRIEFING_TIME):
                    self._run_task('daily_briefing', 'Generate the daily status briefing report')
                    self._last_run['daily_briefing'] = datetime.now().date().isoformat()

                # LinkedIn post generation at 9:00 AM
                if self._should_run_daily('linkedin_post', LINKEDIN_POST_TIME):
                    self._run_task('post_linkedin',
                                   'Generate LinkedIn post drafts based on Business_Goals.md')
                    self._last_run['linkedin_post'] = datetime.now().date().isoformat()

                # Weekly audit every Monday at 7:30 AM
                week_key = f"{datetime.now().isocalendar()[1]}_{datetime.now().year}"
                if self._should_run_weekly('weekly_audit', WEEKLY_AUDIT_DAY, WEEKLY_AUDIT_TIME):
                    self._run_task('weekly_audit',
                                   'Run weekly business audit: review tasks, revenue, subscriptions')
                    self._last_run['weekly_audit'] = week_key

            except Exception as e:
                self.logger.error(f'Scheduler error: {e}')

            time.sleep(60)  # Check every minute

    def stop(self):
        self._stop_event.set()


class Orchestrator:
    """Master process that manages all watchers and scheduled tasks."""

    def __init__(self, vault_path: Path, config: dict):
        self.vault_path = vault_path
        self.config = config
        self.dry_run = config.get('dry_run', False)
        self.watchers: list = []
        self.approval_watcher: ApprovalWatcher = None
        self.scheduler: Scheduler = None
        self._threads: list = []
        self.running = False

    def _build_watcher_processes(self) -> list:
        """Build list of watcher subprocess configs."""
        watchers_dir = Path(__file__).parent / 'watchers'
        vault_str = str(self.vault_path)
        base_flags = ['--dry-run'] if self.dry_run else []

        processes = []

        # File System Watcher (always on)
        if self.config.get('filesystem', True):
            processes.append(WatcherProcess(
                name='FilesystemWatcher',
                command=[PYTHON, str(watchers_dir / 'filesystem_watcher.py'),
                         '--vault', vault_str],
                vault_path=self.vault_path,
                enabled=True
            ))

        # Gmail Watcher
        if self.config.get('gmail', True):
            cmd = [PYTHON, str(watchers_dir / 'gmail_watcher.py'), '--vault', vault_str]
            cmd += base_flags
            processes.append(WatcherProcess(
                name='GmailWatcher',
                command=cmd,
                vault_path=self.vault_path,
                enabled=True
            ))

        # WhatsApp Watcher
        if self.config.get('whatsapp', True):
            cmd = [PYTHON, str(watchers_dir / 'whatsapp_watcher.py'), '--vault', vault_str]
            if self.dry_run:
                cmd.append('--dry-run')
            processes.append(WatcherProcess(
                name='WhatsAppWatcher',
                command=cmd,
                vault_path=self.vault_path,
                enabled=True
            ))

        # LinkedIn Watcher
        if self.config.get('linkedin', True):
            cmd = [PYTHON, str(watchers_dir / 'linkedin_watcher.py'), '--vault', vault_str]
            cmd += base_flags
            processes.append(WatcherProcess(
                name='LinkedInWatcher',
                command=cmd,
                vault_path=self.vault_path,
                enabled=True
            ))

        return processes

    def start(self):
        """Start all watchers, approval watcher, and scheduler."""
        self.running = True
        logger.info('=' * 60)
        logger.info('AI Employee Orchestrator Starting (Silver Tier)')
        logger.info(f'Vault: {self.vault_path}')
        logger.info(f'Dry-run: {self.dry_run}')
        logger.info('=' * 60)

        # Start watcher subprocesses
        self.watchers = self._build_watcher_processes()
        for watcher in self.watchers:
            watcher.start()
            time.sleep(1)  # Stagger starts

        # Start approval watcher thread
        self.approval_watcher = ApprovalWatcher(self.vault_path, self.dry_run)
        t1 = threading.Thread(target=self.approval_watcher.run, daemon=True, name='ApprovalWatcher')
        t1.start()
        self._threads.append(t1)

        # Start scheduler thread
        self.scheduler = Scheduler(self.vault_path, self.dry_run)
        t2 = threading.Thread(target=self.scheduler.run, daemon=True, name='Scheduler')
        t2.start()
        self._threads.append(t2)

        logger.info('All services started. AI Employee is running.')
        logger.info('Press Ctrl+C to stop gracefully.\n')

        # Write startup status to Dashboard
        self._update_dashboard('running')

    def _update_dashboard(self, status: str):
        dashboard = self.vault_path / 'Dashboard.md'
        if not dashboard.exists():
            return
        try:
            content = dashboard.read_text(encoding='utf-8')
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            status_line = f'\n## Orchestrator Status\n- **Status:** {status}\n- **Last update:** {now}\n- **Dry-run:** {self.dry_run}\n'
            if '## Orchestrator Status' in content:
                import re
                content = re.sub(r'\n## Orchestrator Status.*?(?=\n##|\Z)', status_line, content, flags=re.DOTALL)
            else:
                content += status_line
            dashboard.write_text(content, encoding='utf-8')
        except Exception as e:
            logger.warning(f'Could not update Dashboard: {e}')

    def run_forever(self):
        """Main loop: health-check watchers every 60 seconds."""
        self.start()
        try:
            while self.running:
                for watcher in self.watchers:
                    watcher.check_and_restart()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info('\nShutdown signal received...')
        finally:
            self.stop()

    def stop(self):
        """Graceful shutdown."""
        self.running = False
        logger.info('Stopping all services...')

        # Stop approval watcher and scheduler
        if self.approval_watcher:
            self.approval_watcher.stop()
        if self.scheduler:
            self.scheduler.stop()

        # Stop watcher subprocesses
        for watcher in self.watchers:
            watcher.stop()

        self._update_dashboard('stopped')
        logger.info('AI Employee Orchestrator stopped.')


def main():
    parser = argparse.ArgumentParser(
        description='AI Employee — Master Orchestrator (Silver Tier)'
    )
    parser.add_argument('--vault', required=True,
                        help='Absolute path to AI_Employee_Vault folder')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run all watchers in dry-run mode (no real API calls)')
    parser.add_argument('--no-gmail', action='store_true',
                        help='Skip Gmail Watcher (useful before OAuth setup)')
    parser.add_argument('--no-whatsapp', action='store_true',
                        help='Skip WhatsApp Watcher')
    parser.add_argument('--no-linkedin', action='store_true',
                        help='Skip LinkedIn Watcher')
    args = parser.parse_args()

    vault_path = Path(args.vault).resolve()
    if not vault_path.exists():
        print(f'ERROR: Vault not found: {vault_path}')
        sys.exit(1)

    if args.dry_run:
        os.environ['DRY_RUN'] = 'true'

    config = {
        'dry_run': args.dry_run,
        'filesystem': True,
        'gmail': not args.no_gmail,
        'whatsapp': not args.no_whatsapp,
        'linkedin': not args.no_linkedin,
    }

    orchestrator = Orchestrator(vault_path, config)

    # Handle SIGTERM gracefully (for Task Scheduler / PM2)
    def handle_sigterm(signum, frame):
        logger.info('SIGTERM received, shutting down...')
        orchestrator.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    orchestrator.run_forever()


if __name__ == '__main__':
    main()
