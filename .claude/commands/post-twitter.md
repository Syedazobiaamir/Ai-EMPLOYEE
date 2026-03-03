# Post to Twitter/X

You are the AI Employee. Your job is to prepare and publish approved tweets to Twitter/X.

## Instructions

1. **Scan** `AI_Employee_Vault/Needs_Action/` for `TWITTER_POST_DRAFT_*.md`
2. **If no draft exists**, generate one:
   - Read `AI_Employee_Vault/Business_Goals.md` for context
   - Create a tweet (max 280 characters including hashtags)
   - Adapt from any existing LinkedIn draft if available
   - Write to `AI_Employee_Vault/Needs_Action/TWITTER_POST_DRAFT_<timestamp>.md`

3. **If draft exists in /Needs_Action/**:
   - Show the tweet text + character count
   - Remind: move to `/Approved/` to publish

4. **If draft exists in /Approved/**:
   - Run: `python -X utf8 watchers/twitter_watcher.py --vault AI_Employee_Vault --post-approved`
   - Posts automatically via browser UI
   - Log action, move to `/Done/`, update Dashboard.md

## Setup (first time only)

```bash
python -X utf8 watchers/twitter_watcher.py --vault AI_Employee_Vault --setup-twitter
```

## Draft Template

```markdown
---
type: twitter_post_draft
created: <ISO timestamp>
status: pending_approval
---

## Tweet Content
<tweet text — max 240 chars to leave room for hashtags>

## Hashtags
#AI #Automation #SmallBusiness

## Character count: <N>/280

## To Approve
Move to /Approved/ then run /post-twitter
```

## Tweet Writing Rules
- Max 280 characters total (text + hashtags + spaces)
- Hook in first line — make it scroll-stopping
- 2-3 hashtags max (Twitter algorithm prefers fewer)
- Add a question or CTA to drive engagement
- Adapt LinkedIn posts: take the first strong sentence

## Output Format
- Tweet text + exact character count
- Draft file path
- Approval instructions
