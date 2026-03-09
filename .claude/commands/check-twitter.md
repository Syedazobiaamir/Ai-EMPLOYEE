# Check Twitter/X

You are the AI Employee. Your job is to check Twitter/X for engagement and manage pending tweets.

## Instructions

1. **Check session status:**
   - Profile: `config/twitter_profile/`
   - If missing: tell user to run `/setup-sessions` first

2. **Check /Needs_Action/ for pending tweets** (TWITTER_POST_DRAFT_*.md, TWEET_*.md)

3. **If no draft exists, create one:**
   ```bash
   python -X utf8 watchers/twitter_watcher.py --vault AI_Employee_Vault --create-draft
   ```
   - Auto-adapts latest LinkedIn post to tweet format (280 chars)
   - Saves to `/Needs_Action/TWITTER_POST_DRAFT_<timestamp>.md`

4. **If draft exists in /Needs_Action/:**
   - Show tweet text and character count
   - Remind: move to `/Approved/` then run `/post-twitter`

5. **Twitter best practices to include in drafts:**
   - Hook in first 10 words
   - Max 2-3 hashtags (algorithm prefers fewer)
   - Question or CTA drives replies
   - Best times: 8-10 AM, 12-1 PM, 5-6 PM (Tue-Thu)

6. **Engagement monitoring:**
   - Full automation requires Twitter/X API v2 (paid)
   - Free tier: 1,500 tweets/month read, limited analytics
   - For basic monitoring: check manually at x.com

7. **Update Dashboard.md** with last Twitter check timestamp

## Setup Required (first time)
```bash
python -X utf8 watchers/twitter_watcher.py --vault AI_Employee_Vault --setup-twitter
```
Opens x.com — log in and wait for home timeline to load.

## Post Approval Workflow
1. Draft in `/Needs_Action/` → review tweet + char count
2. Move to `/Approved/` → run `/post-twitter`
3. Tweets automatically via browser UI

## Cross-Platform Strategy
When `/post-linkedin` publishes a post, consider creating a tweet with:
- First strong sentence from LinkedIn (max 240 chars)
- 2-3 relevant hashtags
- Link to full post (if public)

## Output Format
- Session status
- Pending tweets count + preview
- Character counts
- Next actions
