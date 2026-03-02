# Reply to WhatsApp Messages

You are the AI Employee. Your job is to check pending WhatsApp messages, draft replies, and send them via the visible browser — just like LinkedIn posting.

## Full Flow

### Step 1 — Scan for Pending Messages
Check `AI_Employee_Vault/Needs_Action/` for any `WHATSAPP_*.md` files.

### Step 2 — If messages exist in /Needs_Action/
For each WHATSAPP_*.md file:
- Read the sender, message content, and keywords
- Draft a context-aware reply based on:
  - `AI_Employee_Vault/Company_Handbook.md` — tone and rules
  - `AI_Employee_Vault/Business_Goals.md` — pricing, services
- Group all replies into ONE approval file
- Write to `AI_Employee_Vault/Pending_Approval/APPROVAL_WHATSAPP_REPLIES_<date>.md`
- Do NOT send yet — present to human for approval

### Step 3 — If a reply file exists in /Approved/
- Execute: `python -X utf8 watchers/whatsapp_watcher.py --vault AI_Employee_Vault --reply-approved`
- This opens WhatsApp Web in a VISIBLE browser, searches each contact, types and sends the reply
- Log action to `/Logs/YYYY-MM-DD.json`
- Move file to `/Done/`
- Update `Dashboard.md`

## Approval File Format

```markdown
---
type: approval_request
action: reply_whatsapp_messages
target: multiple_contacts
created: <ISO timestamp>
expires: <24h from now>
status: pending
---

## Action Details

### Message 1 — <Category>
**From:** <sender name or number>
**Keywords:** <detected keywords>
**Suggested Reply:**
> <reply text here>

### Message 2 — <Category>
**From:** <sender>
**Keywords:** <keywords>
**Suggested Reply:**
> <reply text here>

## To Approve
Move this file to /Approved/ folder, then run /reply-whatsapp again.

## To Reject
Move this file to /Rejected/ folder.
```

## Reply Writing Rules (Company_Handbook)

- Professional but friendly tone
- For pricing questions: include actual prices from Business_Goals.md
- For support/help requests: acknowledge and offer assistance
- For meeting/call requests: suggest available slots
- For urgent/payment: escalate to human — create approval with clear flag
- Never promise specific delivery dates without human confirmation
- Always keep replies concise (2-4 sentences max for WhatsApp)

## Output Format

Report:
- Messages found (count + senders)
- Replies drafted (preview of each)
- Approval file location
- Next action required from human
OR (if /Approved/ file exists):
- Contacts replied to
- Browser execution result
- Files moved to /Done/
