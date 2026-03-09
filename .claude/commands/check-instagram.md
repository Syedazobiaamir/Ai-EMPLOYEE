# Check Instagram & Facebook

You are the AI Employee. Your job is to check Instagram and Facebook for new messages, comments, and engagement.

## Instructions

1. **Check session status:**
   - Profile: `config/instagram_profile/`
   - If missing: tell user to run `/setup-sessions` first

2. **Generate engagement summary:**
   ```bash
   python -X utf8 watchers/instagram_watcher.py --vault AI_Employee_Vault --engagement-summary
   ```

3. **Check /Needs_Action/ for any pending Instagram/Facebook items** (SOCIAL_POST_DRAFT_*.md, INSTAGRAM_POST_*.md, FACEBOOK_POST_*.md)

4. **If pending posts found:**
   - Show draft content
   - Remind user: move to `/Approved/` then run `/post-instagram`

5. **Report engagement metrics** (from Briefings/YYYY-MM-DD_Social_Engagement.md):
   - Recent posts published
   - Engagement summary
   - Recommendations

6. **For DMs / Comments monitoring:**
   - Full automation requires Meta Graph API (business account)
   - Manual check: open Instagram/Facebook in browser
   - Note: Once Meta Graph API is connected via Odoo MCP, this becomes automatic

7. **Update Dashboard.md** with last check timestamp

## Setup Required (first time)
```bash
# Instagram
python -X utf8 watchers/instagram_watcher.py --vault AI_Employee_Vault --setup-instagram

# Facebook
python -X utf8 watchers/instagram_watcher.py --vault AI_Employee_Vault --setup-facebook
```

## Post Approval Workflow
1. Draft exists in `/Needs_Action/` → review content
2. Move to `/Approved/` → run `/post-instagram`
3. Instagram: opens browser with caption ready (attach media manually)
4. Facebook: posts automatically via browser

## Output Format
- Session status (ready / needs setup)
- Pending posts count
- Engagement summary preview
- Next actions
