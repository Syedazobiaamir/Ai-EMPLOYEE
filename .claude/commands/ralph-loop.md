# Ralph Wiggum Loop — Autonomous Task Completion

You are the AI Employee operating in autonomous loop mode (Gold Tier).
The Ralph Wiggum pattern keeps you running until the task is fully complete.

## How It Works

1. You receive a task prompt
2. You work on the task
3. When you try to exit, the Stop hook checks if the task is in /Done
4. If NOT done → Stop hook re-injects your prompt and you try again
5. If DONE → Stop hook allows exit
6. Max iterations prevents infinite loops

## Instructions

### Starting a Ralph Loop

Create the state file at `AI_Employee_Vault/Plans/RALPH_LOOP_STATE.json`:

```json
{
  "task_name": "<short name>",
  "prompt": "<full task description>",
  "task_file": "<filename in /Needs_Action that moves to /Done when complete>",
  "completion_promise": "TASK_COMPLETE",
  "max_iterations": 10,
  "current_iteration": 0,
  "created": "<ISO timestamp>",
  "last_retry": null
}
```

### Completing a Task (Promise-based)

When the task is done, output this exact string:
```
<promise>TASK_COMPLETE</promise>
```
AND create: `AI_Employee_Vault/Plans/RALPH_DONE_TASK_COMPLETE.txt`

### Completing a Task (File-movement)

Move the task file from `/Needs_Action/` → `/Done/`
The Stop hook will detect this automatically.

### Cancelling a Loop

Delete: `AI_Employee_Vault/Plans/RALPH_LOOP_STATE.json`

---

## Example: Process All Inbox Items Autonomously

Create state file then run:
```
python .claude/hooks/stop.py  # test the hook
```

The agent will keep processing items until /Needs_Action is empty.

---

## Current Loop Status

Check `AI_Employee_Vault/Plans/RALPH_LOOP_STATE.json` for:
- task_name: what's running
- current_iteration: how many retries
- max_iterations: limit

## Output

After starting a loop, report:
- Task name and prompt
- State file created
- Max iterations set
- How to monitor progress (check Dashboard.md)
