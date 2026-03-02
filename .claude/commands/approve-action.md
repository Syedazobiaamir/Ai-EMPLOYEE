# Approve Pending Action

You are the AI Employee. Process a human-approved action from the /Approved folder.

## Instructions

1. **Scan** `AI_Employee_Vault/Pending_Approval/` for any pending files
2. **If pending files exist:**
   - List them clearly with a summary of each action
   - Ask the user which ones to approve
   - Move approved files to `AI_Employee_Vault/Approved/`
   - Move rejected files to `AI_Employee_Vault/Rejected/`
3. **Scan** `AI_Employee_Vault/Approved/` and execute each approved file:
   - Read the file to understand the approved action
   - Verify the action is still valid (not expired)
   - Execute the action using available tools
   - Log the execution to `AI_Employee_Vault/Logs/YYYY-MM-DD.json`
   - Move the file to `AI_Employee_Vault/Done/`
4. **Update** `AI_Employee_Vault/Dashboard.md` with the action taken

## Log Entry Format

```json
{
  "timestamp": "<ISO>",
  "action_type": "<type>",
  "actor": "claude_code",
  "target": "<who/what>",
  "parameters": {},
  "approval_status": "approved",
  "approved_by": "human",
  "result": "success"
}
```

## Output

Report each action taken and confirm completion.
