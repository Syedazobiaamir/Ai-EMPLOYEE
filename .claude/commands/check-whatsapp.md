# Check WhatsApp

You are the AI Employee. Your job is to scan WhatsApp for new business messages and process them.

## Instructions

1. **Check if WhatsApp profile exists:**
   - Profile dir: `config/whatsapp_profile/`
   - If missing: tell user to run `python -X utf8 watchers/whatsapp_watcher.py --vault AI_Employee_Vault --setup-whatsapp`

2. **Run one WhatsApp scan cycle:**
   ```
   python -X utf8 watchers/whatsapp_watcher.py --vault AI_Employee_Vault --once
   ```
   If `--once` flag not supported, run with a short timeout:
   ```
   python -X utf8 -c "
   import sys; sys.path.insert(0, 'watchers')
   from whatsapp_watcher import WhatsAppWatcher
   w = WhatsAppWatcher(vault_path='AI_Employee_Vault')
   msgs = w.check_for_updates()
   print(f'Found {len(msgs)} new message(s)')
   for m in msgs:
       f = w.create_action_file(m)
       if f: print(f'Created: {f.name}')
   if not msgs: print('No new business messages found.')
   "
   ```

3. **Report results:**
   - How many new messages were found
   - Who sent them and what keywords were detected
   - Action files created in `/Needs_Action/`

4. **If new messages found:**
   - Read each `WHATSAPP_*.md` in `/Needs_Action/`
   - Draft appropriate replies based on message type:
     - Greeting → warm welcome + introduce services
     - Price inquiry → reply with product prices
     - Order → confirm and ask for delivery address
     - Complaint → flag for human review, do NOT auto-reply
     - Collaboration → ask for details
   - Create ONE consolidated approval file: `/Pending_Approval/APPROVAL_WHATSAPP_REPLIES_<date>.md`
   - Do NOT send — wait for human to move to `/Approved/`

5. **Remind user:**
   - To approve: move approval file to `/Approved/`
   - To send: run `/reply-whatsapp`

6. **Update Dashboard.md** with last WhatsApp check timestamp

## Start Continuous Watcher (optional)
To run in background polling every 30 seconds:
```
python -X utf8 watchers/whatsapp_watcher.py --vault AI_Employee_Vault
```

## Output Format
Report:
- WhatsApp account status (connected / needs setup)
- Number of new messages found
- Senders and message types
- Approval file created (if any)
- Next step instructions
