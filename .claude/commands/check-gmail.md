# Check Gmail

You are the AI Employee. Your job is to check Gmail for new important emails and process them.

## Instructions

1. **Re-authenticate if needed** — check if `config/gmail_token.json` exists:
   - If missing or expired: run `python -X utf8 watchers/gmail_watcher.py --vault AI_Employee_Vault --auth`

2. **Run one Gmail poll cycle**:
   ```
   python -X utf8 -c "
   import sys; sys.path.insert(0, 'watchers')
   from gmail_watcher import GmailWatcher
   w = GmailWatcher(vault_path='AI_Employee_Vault')
   msgs = w.check_for_updates()
   print(f'Found {len(msgs)} new message(s)')
   for m in msgs:
       f = w.create_action_file(m)
       if f: print(f'Created: {f.name}')
   if not msgs: print('No new important unread emails.')
   "
   ```

3. **Report results:**
   - How many new emails were found
   - What action files were created in `/Needs_Action/`
   - If 0 found: confirm watcher is healthy and no action needed

4. **If new emails found:**
   - Read each new `EMAIL_*.md` file in `/Needs_Action/`
   - Draft reply for each one
   - Create approval file in `/Pending_Approval/APPROVAL_EMAIL_<desc>_<date>.md`
   - Remind user to move to `/Approved/` then run `/send-email`

5. **Update Dashboard.md** with last checked timestamp

## Start Continuous Watcher (optional)
To run in background polling every 2 minutes:
```
python -X utf8 watchers/gmail_watcher.py --vault AI_Employee_Vault
```

## Output Format
Report:
- Gmail account checked
- Number of new emails found
- List of action files created (if any)
- Approval files created (if any)
- Next step instructions
