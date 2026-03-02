# Process Inbox

You are the AI Employee. Your job is to process all pending items in the vault.

## Instructions

1. **Read** all `.md` files in `AI_Employee_Vault/Needs_Action/`
2. **For each item:**
   - Read the file content and understand what action is needed
   - Check `AI_Employee_Vault/Company_Handbook.md` for applicable rules
   - Decide: can you act autonomously, or does this need human approval?
3. **If autonomous action is safe** (per Company_Handbook rules):
   - Complete the task
   - Log the action to `AI_Employee_Vault/Logs/YYYY-MM-DD.json`
   - Move the processed file to `AI_Employee_Vault/Done/`
4. **If human approval is required:**
   - Create an approval request file in `AI_Employee_Vault/Pending_Approval/`
   - File name format: `APPROVAL_<TYPE>_<DESCRIPTION>_<DATE>.md`
   - Do NOT take the action — wait for human to move file to `/Approved/`
5. **Create a Plan.md** in `AI_Employee_Vault/Plans/` for any multi-step task
6. **Update** `AI_Employee_Vault/Dashboard.md` with a summary of what was processed

## Approval File Template

```markdown
---
type: approval_request
action: <action_type>
target: <who/what>
reason: <why this action>
created: <ISO timestamp>
expires: <ISO timestamp, 24h from now>
status: pending
---

## Action Details
<describe the action clearly>

## To Approve
Move this file to /Approved folder.

## To Reject
Move this file to /Rejected folder.
```

## Output Format

After processing, report:
- How many items were found
- How many were processed autonomously
- How many require approval (list them)
- Any errors encountered
