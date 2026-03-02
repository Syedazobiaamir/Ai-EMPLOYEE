# Check Vault Health

You are the AI Employee. Perform a health check on the entire vault and report status.

## Instructions

1. **Verify** all required folders exist:
   - `AI_Employee_Vault/Inbox`
   - `AI_Employee_Vault/Needs_Action`
   - `AI_Employee_Vault/Done`
   - `AI_Employee_Vault/Logs`
   - `AI_Employee_Vault/Plans`
   - `AI_Employee_Vault/Pending_Approval`
   - `AI_Employee_Vault/Approved`
   - `AI_Employee_Vault/Rejected`

2. **Verify** required files exist:
   - `AI_Employee_Vault/Dashboard.md`
   - `AI_Employee_Vault/Company_Handbook.md`
   - `AI_Employee_Vault/Business_Goals.md`

3. **Count** items in each folder

4. **Check** for stale items (files older than 48 hours in /Needs_Action or /Pending_Approval)

5. **Check** for expired approval requests (past their `expires` date)

6. **Update** `AI_Employee_Vault/Dashboard.md` with current health status and item counts

## Output Format

Report as a clean table:
```
VAULT HEALTH CHECK — <timestamp>
================================
Folder              | Count | Status
--------------------|-------|-------
Inbox               |   0   | OK
Needs_Action        |   0   | OK
Pending_Approval    |   0   | OK
Done                |   0   | OK
Logs                |   0   | OK

Required Files      | Exists | Status
--------------------|--------|-------
Dashboard.md        |  YES   | OK
Company_Handbook.md |  YES   | OK
Business_Goals.md   |  YES   | OK

ALERTS:
<list any stale items, missing folders, or expired approvals>

Overall Status: HEALTHY / NEEDS ATTENTION
```
