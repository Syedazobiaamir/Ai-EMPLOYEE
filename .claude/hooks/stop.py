#!/usr/bin/env python3
"""
Ralph Wiggum Stop Hook — Gold Tier
===================================
Intercepts Claude Code's exit signal. If an active ralph-loop task
is NOT yet in /Done, re-injects the prompt to keep the agent running.

How it works:
  1. Claude Code calls this script before exiting
  2. We check AI_Employee_Vault/Plans/RALPH_LOOP_STATE.json for active task
  3. If task file exists in /Done → allow exit (task complete)
  4. If task NOT in /Done and iterations < max → block exit, re-inject prompt
  5. If max iterations reached → allow exit with warning

Usage (set in Claude Code settings):
  hooks:
    Stop: ["python .claude/hooks/stop.py"]

Environment variables passed by Claude Code:
  CLAUDE_HOOK_STOP_REASON   - why Claude is stopping
  CLAUDE_WORKSPACE          - working directory
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

VAULT = Path("AI_Employee_Vault")
STATE_FILE = VAULT / "Plans" / "RALPH_LOOP_STATE.json"
LOG_FILE = VAULT / "Logs" / f"{datetime.now().strftime('%Y-%m-%d')}.json"


def load_state():
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def log_action(action_type, result, details=""):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "actor": "ralph_wiggum_hook",
        "target": "claude_code_exit",
        "parameters": {"details": details},
        "approval_status": "auto",
        "approved_by": "system",
        "result": result,
    }
    entries = []
    if LOG_FILE.exists():
        try:
            entries = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            entries = []
    entries.append(entry)
    LOG_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def task_is_done(state):
    """Check if the task file has been moved to /Done."""
    task_file = state.get("task_file")
    if not task_file:
        # Promise-based completion: check if promise was output
        promise = state.get("completion_promise", "TASK_COMPLETE")
        done_marker = VAULT / "Plans" / f"RALPH_DONE_{promise}.txt"
        return done_marker.exists()

    # File-movement based: check if task file is in /Done
    done_path = VAULT / "Done" / Path(task_file).name
    return done_path.exists()


def main():
    state = load_state()

    # No active ralph loop — allow exit normally
    if state is None:
        sys.exit(0)

    task_prompt = state.get("prompt", "")
    max_iterations = state.get("max_iterations", 10)
    current_iteration = state.get("current_iteration", 0)
    task_name = state.get("task_name", "unnamed_task")

    # Check if task is already done
    if task_is_done(state):
        print(f"[Ralph Wiggum] Task '{task_name}' COMPLETE after {current_iteration} iteration(s). Allowing exit.")
        log_action("ralph_loop_complete", "success", f"Task '{task_name}' completed in {current_iteration} iterations")
        STATE_FILE.unlink(missing_ok=True)
        sys.exit(0)

    # Check max iterations
    if current_iteration >= max_iterations:
        print(f"[Ralph Wiggum] Max iterations ({max_iterations}) reached for '{task_name}'. Allowing exit.")
        log_action("ralph_loop_max_iterations", "warning", f"Task '{task_name}' hit max iterations ({max_iterations})")
        STATE_FILE.unlink(missing_ok=True)
        sys.exit(0)

    # Task not done — increment iteration and re-inject prompt
    state["current_iteration"] = current_iteration + 1
    state["last_retry"] = datetime.now().isoformat()
    save_state(state)

    print(f"[Ralph Wiggum] Task '{task_name}' not complete (iteration {current_iteration + 1}/{max_iterations}). Re-injecting prompt...")
    log_action("ralph_loop_retry", "success", f"Task '{task_name}' retry {current_iteration + 1}/{max_iterations}")

    # Output the prompt to re-inject (Claude Code reads stdout from Stop hook)
    print(f"\n{task_prompt}")

    # Exit code 2 = block exit and re-inject (Claude Code convention)
    sys.exit(2)


if __name__ == "__main__":
    main()
