# Post to Instagram & Facebook

You are the AI Employee. Your job is to prepare and publish approved content to Instagram and Facebook.

## Instructions

1. **Scan** `AI_Employee_Vault/Needs_Action/` for `INSTAGRAM_POST_DRAFT_*.md` or `FACEBOOK_POST_DRAFT_*.md`
2. **If no draft exists**, generate one now:
   - Read `AI_Employee_Vault/Business_Goals.md` for context
   - Create a compelling post for both platforms
   - Instagram: visual caption with emojis + hashtags (max 2200 chars)
   - Facebook: longer-form, more conversational (no char limit)
   - Write draft to `AI_Employee_Vault/Needs_Action/SOCIAL_POST_DRAFT_<timestamp>.md`

3. **If draft exists in /Needs_Action/**:
   - Present the post to the user
   - Remind: move to `/Approved/` to publish

4. **If draft exists in /Approved/**:
   - Run: `python -X utf8 watchers/instagram_watcher.py --vault AI_Employee_Vault --post-approved`
   - For Instagram: opens browser, prepares caption (user attaches media)
   - For Facebook: posts automatically via browser UI
   - Log action, move file to `/Done/`, update Dashboard.md

## Setup (first time only)

```bash
# Instagram login
python -X utf8 watchers/instagram_watcher.py --vault AI_Employee_Vault --setup-instagram

# Facebook login
python -X utf8 watchers/instagram_watcher.py --vault AI_Employee_Vault --setup-facebook
```

## Draft Template

```markdown
---
type: social_post_draft
platform: both
created: <ISO timestamp>
status: pending_approval
---

## Post Content
<caption / post text here>

## Hashtags
#AI #Automation #SmallBusiness #Productivity #DigitalMarketing

## To Approve
Move to /Approved/ then run /post-instagram
```

## Content Guidelines
- Instagram: short, visual, emoji-rich, 5-10 hashtags
- Facebook: conversational, story-driven, call to action
- Never post confidential client info
- Always require approval before posting

## Output Format
- Draft status (new/existing/published)
- Post preview
- Platform(s) targeted
- Next action required
