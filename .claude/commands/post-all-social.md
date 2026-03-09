# Post to All Social Media (Instagram + Facebook + Twitter)

You are the AI Employee. Your job is to publish one piece of approved content across ALL three platforms — Instagram, Facebook, and Twitter/X — automatically in sequence.

## This is Gold Tier Automation
One approval → three platforms → zero manual work.

---

## Instructions

### Step 1 — Check for Approved Content

Scan `AI_Employee_Vault/Approved/` for any of:
- `SOCIAL_POST_DRAFT_*.md`
- `INSTAGRAM_POST_DRAFT_*.md`
- `FACEBOOK_POST_DRAFT_*.md`
- `LINKEDIN_POST_DRAFT_*.md` (will be adapted)

### Step 2 — If NO approved content exists

Generate fresh content for all platforms:

1. Read `AI_Employee_Vault/Business_Goals.md` for context
2. Create a master post draft saved to `AI_Employee_Vault/Needs_Action/SOCIAL_POST_DRAFT_<timestamp>.md`:

```markdown
---
type: social_post_draft
platforms: instagram, facebook, twitter
created: <ISO timestamp>
status: pending_approval
requires_approval: true
---

## Instagram Caption
<visual, emoji-rich caption, 5-10 hashtags, max 2200 chars>

## Facebook Post
<conversational, story-driven, 80-150 words, 1-2 hashtags>

## Tweet (280 chars max)
<hook + value + 2-3 hashtags, exact char count shown>
Character count: XX/280

## To Approve
Move this file to /Approved/ then run /post-all-social
```

Then tell the user: "Draft created in /Needs_Action/ — review and move to /Approved/ to publish to all 3 platforms."

### Step 3 — If approved content EXISTS

Execute in this order:

#### 3a. Instagram Post
```bash
python -X utf8 watchers/instagram_watcher.py --vault AI_Employee_Vault --post-approved
```
- Uploads image from `config/instagram_post.jpg` (1080x1080)
- Types caption automatically
- Clicks Share — fully automated
- Wait for confirmation

#### 3b. Facebook Post
```bash
python -X utf8 post_facebook_browser.py
```
- Opens browser to Facebook
- Types post text automatically
- Clicks Post — fully automated
- Wait for confirmation

#### 3c. Twitter/X Post
```bash
python -X utf8 watchers/twitter_watcher.py --vault AI_Employee_Vault --post-approved
```
- Opens browser to x.com
- Uses execCommand to type into DraftJS editor
- Clicks Post via JS click — fully automated
- Wait for confirmation

### Step 4 — After All Three Post

1. Move the source file from `/Approved/` to `/Done/`
2. Log all three actions to `AI_Employee_Vault/Logs/YYYY-MM-DD.json`:
```json
{
  "timestamp": "<ISO>",
  "action_type": "cross_platform_social_post",
  "actor": "claude_code",
  "target": "instagram, facebook, twitter",
  "approval_status": "approved",
  "approved_by": "human",
  "result": "success"
}
```
3. Update `AI_Employee_Vault/Dashboard.md`:
   - Last social post timestamp
   - Platforms posted to
   - Post preview (first 80 chars)

---

## Setup (first time only)

```bash
# Instagram + Facebook (shared session)
python -X utf8 watchers/instagram_watcher.py --vault AI_Employee_Vault --setup-instagram

# Twitter/X
python -X utf8 watchers/twitter_watcher.py --vault AI_Employee_Vault --setup-twitter

# LinkedIn (optional, separate)
python -X utf8 watchers/linkedin_watcher.py --vault AI_Employee_Vault --setup-linkedin
```

Sessions saved at:
- `config/instagram_profile/` → Instagram + Facebook
- `config/twitter_profile/` → Twitter/X
- `config/linkedin_session.json` → LinkedIn

---

## Content Adaptation Rules

When adapting ONE piece of content for 3 platforms:

| Platform | Tone | Length | Hashtags | Media |
|----------|------|--------|----------|-------|
| Instagram | Visual, emoji-rich | 150-300 chars caption | 5-10 | Required (1080x1080) |
| Facebook | Conversational, story | 80-150 words | 1-2 | Optional |
| Twitter | Hook, punchy | Max 280 chars | 2-3 | Optional |

---

## Output Format

After completing, report:
```
Cross-Platform Post Complete
============================
Instagram:  ✅ Posted — nayaaborganics.pk
Facebook:   ✅ Posted — Zobia Muhammad Amir
Twitter/X:  ✅ Posted — @zobiaamir281

Content: "<first 80 chars of post>..."
Logged to: AI_Employee_Vault/Logs/<date>.json
Moved to:  AI_Employee_Vault/Done/<filename>
```
