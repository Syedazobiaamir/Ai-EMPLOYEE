#!/usr/bin/env python3
"""
setup_task_scheduler.py — Windows Task Scheduler Setup for AI Employee (Silver Tier)

Creates Windows Task Scheduler tasks to:
1. Start the Orchestrator on user login (persistent watchers)
2. Run daily briefing at 8:00 AM
3. Run weekly business audit on Monday at 7:30 AM

Also provides:
- List all AI Employee scheduled tasks
- Remove all AI Employee scheduled tasks

Usage:
    python scheduler/setup_task_scheduler.py --vault ./AI_Employee_Vault --install
    python scheduler/setup_task_scheduler.py --vault ./AI_Employee_Vault --list
    python scheduler/setup_task_scheduler.py --vault ./AI_Employee_Vault --remove

Requirements:
    - Windows only (uses schtasks.exe)
    - Run as Administrator for Task Scheduler access
    - Python must be in PATH

For Linux/Mac (cron alternative):
    See scheduler/crontab_setup.sh
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TASK_PREFIX = 'AIEmployee'


def is_windows() -> bool:
    return sys.platform == 'win32'


def run_schtasks(args: list) -> tuple:
    """Run schtasks.exe with given arguments."""
    cmd = ['schtasks'] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, '', 'schtasks.exe not found — are you on Windows?'


def create_orchestrator_task(vault_path: Path, python_path: str, project_path: Path) -> bool:
    """Create task: Start Orchestrator on user login."""
    task_name = f'{TASK_PREFIX}_Orchestrator'
    script = str(project_path / 'orchestrator.py')
    vault = str(vault_path)

    cmd_args = [
        '/Create', '/F',  # Force overwrite
        '/TN', task_name,
        '/TR', f'"{python_path}" "{script}" --vault "{vault}" --no-gmail',
        '/SC', 'ONLOGON',
        '/DELAY', '0001:00',  # 1 minute delay after login
        '/RL', 'HIGHEST',
        '/IT',  # Only run when user is logged in
    ]

    code, out, err = run_schtasks(cmd_args)
    if code == 0:
        print(f'[OK] Created task: {task_name}')
        print(f'  Trigger: On user login (with 1-min delay)')
        print(f'  Command: {python_path} {script} --vault {vault} --no-gmail')
        return True
    else:
        print(f'[FAIL] Failed to create {task_name}: {err.strip() or out.strip()}')
        return False


def create_daily_briefing_task(vault_path: Path, python_path: str, project_path: Path) -> bool:
    """Create task: Daily briefing at 8:00 AM."""
    task_name = f'{TASK_PREFIX}_DailyBriefing'
    # Uses claude CLI to run the daily-briefing skill
    # Note: This assumes claude is installed globally
    claude_cmd = f'claude --print "/daily-briefing"'

    cmd_args = [
        '/Create', '/F',
        '/TN', task_name,
        '/TR', f'cmd /c "cd /d "{project_path}" && {claude_cmd}"',
        '/SC', 'DAILY',
        '/ST', '08:00',
        '/RL', 'HIGHEST',
    ]

    code, out, err = run_schtasks(cmd_args)
    if code == 0:
        print(f'[OK] Created task: {task_name}')
        print(f'  Trigger: Daily at 08:00')
        return True
    else:
        print(f'[FAIL] Failed to create {task_name}: {err.strip() or out.strip()}')
        return False


def create_weekly_audit_task(vault_path: Path, python_path: str, project_path: Path) -> bool:
    """Create task: Weekly audit every Monday at 7:30 AM."""
    task_name = f'{TASK_PREFIX}_WeeklyAudit'
    claude_cmd = f'claude --print "/weekly-audit"'

    cmd_args = [
        '/Create', '/F',
        '/TN', task_name,
        '/TR', f'cmd /c "cd /d "{project_path}" && {claude_cmd}"',
        '/SC', 'WEEKLY',
        '/D', 'MON',
        '/ST', '07:30',
        '/RL', 'HIGHEST',
    ]

    code, out, err = run_schtasks(cmd_args)
    if code == 0:
        print(f'[OK] Created task: {task_name}')
        print(f'  Trigger: Every Monday at 07:30')
        return True
    else:
        print(f'[FAIL] Failed to create {task_name}: {err.strip() or out.strip()}')
        return False


def create_linkedin_post_task(vault_path: Path, python_path: str, project_path: Path) -> bool:
    """Create task: LinkedIn post generation check at 9:00 AM."""
    task_name = f'{TASK_PREFIX}_LinkedInPost'
    script = str(project_path / 'watchers' / 'linkedin_watcher.py')
    vault = str(vault_path)

    cmd_args = [
        '/Create', '/F',
        '/TN', task_name,
        '/TR', f'"{python_path}" "{script}" --vault "{vault}" --generate-post',
        '/SC', 'DAILY',
        '/ST', '09:00',
        '/RL', 'HIGHEST',
    ]

    code, out, err = run_schtasks(cmd_args)
    if code == 0:
        print(f'[OK] Created task: {task_name}')
        print(f'  Trigger: Daily at 09:00 (LinkedIn post draft generation)')
        return True
    else:
        print(f'[FAIL] Failed to create {task_name}: {err.strip() or out.strip()}')
        return False


def list_tasks() -> None:
    """List all AI Employee scheduled tasks."""
    code, out, err = run_schtasks(['/Query', '/FO', 'LIST', '/NH'])
    if code != 0:
        print(f'Error listing tasks: {err}')
        return

    print(f'\n{"=" * 50}')
    print(f'AI Employee Scheduled Tasks ({TASK_PREFIX}_*)')
    print(f'{"=" * 50}')

    lines = out.split('\n')
    ai_tasks = []
    current_task = {}

    for line in lines:
        line = line.strip()
        if line.startswith('TaskName:') and TASK_PREFIX in line:
            if current_task:
                ai_tasks.append(current_task)
            current_task = {'name': line.split(':', 1)[1].strip()}
        elif current_task:
            if line.startswith('Status:'):
                current_task['status'] = line.split(':', 1)[1].strip()
            elif line.startswith('Next Run Time:'):
                current_task['next_run'] = line.split(':', 1)[1].strip()
            elif line.startswith('Last Run Time:'):
                current_task['last_run'] = line.split(':', 1)[1].strip()

    if current_task:
        ai_tasks.append(current_task)

    if not ai_tasks:
        print('No AI Employee tasks found.')
        print('Run with --install to create them.')
    else:
        for task in ai_tasks:
            print(f"\nTask: {task.get('name', 'unknown')}")
            print(f"  Status:   {task.get('status', 'unknown')}")
            print(f"  Next Run: {task.get('next_run', 'unknown')}")
            print(f"  Last Run: {task.get('last_run', 'never')}")

    print()


def remove_tasks() -> None:
    """Remove all AI Employee scheduled tasks."""
    task_names = [
        f'{TASK_PREFIX}_Orchestrator',
        f'{TASK_PREFIX}_DailyBriefing',
        f'{TASK_PREFIX}_WeeklyAudit',
        f'{TASK_PREFIX}_LinkedInPost',
    ]
    print('Removing AI Employee scheduled tasks...')
    for task_name in task_names:
        code, out, err = run_schtasks(['/Delete', '/TN', task_name, '/F'])
        if code == 0:
            print(f'[OK] Removed: {task_name}')
        else:
            print(f'  Skipped {task_name} (may not exist)')


def generate_crontab() -> str:
    """Generate crontab entries for Linux/Mac (alternative to Task Scheduler)."""
    return """# AI Employee Crontab Entries (Linux/Mac)
# Add with: crontab -e

# Start orchestrator on reboot
@reboot sleep 60 && cd /path/to/project && python orchestrator.py --vault AI_Employee_Vault --no-gmail >> logs/orchestrator.log 2>&1

# Daily briefing at 8:00 AM
0 8 * * * cd /path/to/project && claude --print "/daily-briefing" >> logs/briefing.log 2>&1

# LinkedIn post draft at 9:00 AM
0 9 * * * cd /path/to/project && python watchers/linkedin_watcher.py --vault AI_Employee_Vault --generate-post >> logs/linkedin.log 2>&1

# Weekly audit every Monday at 7:30 AM
30 7 * * 1 cd /path/to/project && claude --print "/daily-briefing" >> logs/weekly_audit.log 2>&1
"""


def write_schedule_config(vault_path: Path, project_path: Path) -> None:
    """Write schedule configuration JSON for reference."""
    config = {
        "version": "1.0",
        "created": datetime.now().isoformat(),
        "platform": "windows",
        "tasks": [
            {
                "name": f"{TASK_PREFIX}_Orchestrator",
                "description": "Start AI Employee Orchestrator on login",
                "trigger": "on_login",
                "delay": "1_minute",
                "command": f"python orchestrator.py --vault AI_Employee_Vault --no-gmail"
            },
            {
                "name": f"{TASK_PREFIX}_DailyBriefing",
                "description": "Generate daily status briefing",
                "trigger": "daily_at_08:00",
                "command": "claude --print '/daily-briefing'"
            },
            {
                "name": f"{TASK_PREFIX}_LinkedInPost",
                "description": "Generate LinkedIn post draft",
                "trigger": "daily_at_09:00",
                "command": "python watchers/linkedin_watcher.py --vault AI_Employee_Vault --generate-post"
            },
            {
                "name": f"{TASK_PREFIX}_WeeklyAudit",
                "description": "Weekly business audit",
                "trigger": "monday_at_07:30",
                "command": "claude --print '/daily-briefing'"
            }
        ]
    }
    config_file = project_path / 'scheduler' / 'schedule_config.json'
    config_file.write_text(json.dumps(config, indent=2), encoding='utf-8')
    print(f'Schedule config saved: {config_file}')


def main():
    parser = argparse.ArgumentParser(
        description='AI Employee — Task Scheduler Setup (Silver Tier)'
    )
    parser.add_argument('--vault', required=True,
                        help='Absolute path to AI_Employee_Vault folder')
    parser.add_argument('--install', action='store_true',
                        help='Create all scheduled tasks')
    parser.add_argument('--list', action='store_true',
                        help='List existing AI Employee tasks')
    parser.add_argument('--remove', action='store_true',
                        help='Remove all AI Employee tasks')
    parser.add_argument('--crontab', action='store_true',
                        help='Print crontab entries for Linux/Mac')
    args = parser.parse_args()

    vault_path = Path(args.vault).resolve()
    project_path = Path(__file__).parent.parent.resolve()

    if args.crontab:
        print(generate_crontab())
        return

    if args.list:
        if not is_windows():
            print('Task Scheduler is Windows-only. Use --crontab for Linux/Mac.')
        else:
            list_tasks()
        return

    if args.remove:
        if not is_windows():
            print('Task Scheduler is Windows-only.')
        else:
            remove_tasks()
        return

    if args.install:
        if not is_windows():
            print('Task Scheduler is Windows-only. For Linux/Mac, use:')
            print(generate_crontab())
            return

        print(f'\nInstalling AI Employee Scheduled Tasks')
        print(f'Project: {project_path}')
        print(f'Vault: {vault_path}')
        print(f'Python: {sys.executable}')
        print('-' * 50)

        success = True
        success &= create_orchestrator_task(vault_path, sys.executable, project_path)
        success &= create_daily_briefing_task(vault_path, sys.executable, project_path)
        success &= create_linkedin_post_task(vault_path, sys.executable, project_path)
        success &= create_weekly_audit_task(vault_path, sys.executable, project_path)

        write_schedule_config(vault_path, project_path)

        print('\n' + ('=' * 50))
        if success:
            print('[OK] All tasks installed successfully!')
            print('\nThe AI Employee will now:')
            print('  - Start automatically when you log in')
            print('  - Generate daily briefing at 8:00 AM')
            print('  - Draft LinkedIn posts at 9:00 AM')
            print('  - Run weekly audit every Monday at 7:30 AM')
        else:
            print('[WARN]  Some tasks failed. Try running as Administrator.')
            print('  Right-click terminal → Run as Administrator → retry')

        return

    parser.print_help()


if __name__ == '__main__':
    main()
