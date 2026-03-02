# Post to LinkedIn

You are the AI Employee. Your job is to prepare and publish approved LinkedIn content.

## Instructions

1. **Scan** `AI_Employee_Vault/Needs_Action/` for any `LINKEDIN_POST_DRAFT_*.md` files
2. **If no draft exists**, generate one now:
   - Read `AI_Employee_Vault/Business_Goals.md` for context
   - Read `AI_Employee_Vault/Dashboard.md` for recent activity
   - Create a compelling LinkedIn post that showcases business value
   - Write the draft to `AI_Employee_Vault/Needs_Action/LINKEDIN_POST_DRAFT_<timestamp>.md`
3. **If a draft exists in /Needs_Action**:
   - Read it and present the post options to the user
   - Wait — do NOT publish without approval
   - Remind the user to move the file to `/Approved/` to publish
4. **If a draft exists in /Approved/**:
   - Read the approved post content
   - Execute: `python watchers/linkedin_watcher.py --vault AI_Employee_Vault --post-approved`
   - Log the action to `/Logs/YYYY-MM-DD.json`
   - Move the file to `/Done/`
   - Update `Dashboard.md`

## LinkedIn Post Draft Template

```markdown
---
type: linkedin_post_draft
created: <ISO timestamp>
status: pending_approval
requires_approval: true
action: post_to_linkedin
---

## LinkedIn Post Draft

### Option A: Value/Tips Post
```
[Post content here]
```

### Option B: Service Showcase
```
[Post content here]
```

## To Approve
Move this file to /Approved/ folder, then run /post-linkedin again.
```

## Content Guidelines (from Company_Handbook)

- Only post pre-approved content (requires human review)
- Never post about competitors
- Never share confidential client information
- Use professional tone
- Include relevant hashtags (#AI #Automation #Productivity etc.)
- Best posting times: Tue-Thu, 8-10 AM or 5-6 PM

## Output Format

Report:
- Draft status (new/existing/published)
- Post preview (first 200 chars)
- Next action required from human
