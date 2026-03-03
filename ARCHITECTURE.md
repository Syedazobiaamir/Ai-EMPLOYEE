# AI Employee — Architecture & Lessons Learned

**Project:** Personal AI Employee Hackathon 0 — Building Autonomous FTEs in 2026
**Tier:** Gold (Full Autonomous Employee)
**Author:** Zobia Amir
**Stack:** Claude Code + Obsidian + Playwright + Gmail API + MCP Servers

---

## System Overview

The AI Employee is a local-first, human-in-the-loop autonomous agent that manages personal and business affairs 24/7. It combines:

- **Claude Code** as the reasoning brain (executor + decision maker)
- **Obsidian vault** as memory, dashboard, and audit trail
- **Python watchers** as senses (monitoring Gmail, WhatsApp, LinkedIn, Instagram, Twitter)
- **MCP servers** as hands (sending emails, interacting with Odoo, browsing web)
- **Ralph Wiggum loop** for persistence (autonomous multi-step task completion)

```
┌─────────────────────────────────────────────────────────┐
│                    HUMAN OPERATOR                        │
│           (approves actions, reviews briefings)          │
└───────────────────────┬─────────────────────────────────┘
                        │ Approval (move files to /Approved/)
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  CLAUDE CODE (Brain)                     │
│         Skills (slash commands in .claude/commands/)     │
│         Ralph Wiggum Loop (stop hook)                    │
└──────┬──────────────────────────────────────────────────┘
       │ reads/writes
       ▼
┌─────────────────────────────────────────────────────────┐
│               OBSIDIAN VAULT (Memory)                    │
│  /Inbox → /Needs_Action → /Pending_Approval             │
│  /Approved → /Done  |  /Logs  |  /Briefings             │
└──────┬──────────────────────────────────────────────────┘
       │ monitors
       ▼
┌─────────────────────────────────────────────────────────┐
│                 WATCHERS (Senses)                        │
│  gmail_watcher.py   — Gmail API polling (2min)          │
│  whatsapp_watcher.py — WhatsApp Web browser (30s)       │
│  linkedin_watcher.py — LinkedIn browser + posting       │
│  instagram_watcher.py — Instagram/Facebook browser      │
│  twitter_watcher.py  — Twitter/X browser                │
│  filesystem_watcher.py — /Inbox file drops              │
└──────┬──────────────────────────────────────────────────┘
       │ executes
       ▼
┌─────────────────────────────────────────────────────────┐
│                MCP SERVERS (Hands)                       │
│  email_mcp    — Gmail send/draft/search                 │
│  odoo_mcp     — Accounting, invoices, customers         │
│  browser_mcp  — General web browsing                    │
└─────────────────────────────────────────────────────────┘
```

---

## Tier Progression

### Bronze (Foundation)
- Obsidian vault structure
- FilesystemWatcher (file drop detection)
- 4 core skills: /process-inbox, /daily-briefing, /check-vault, /approve-action
- Manual Claude Code invocation

### Silver (Active Watchers)
- GmailWatcher (OAuth2, Gmail API)
- WhatsAppWatcher (Playwright persistent profile)
- LinkedInWatcher (Playwright browser UI posting)
- Email MCP server (Node.js, googleapis)
- Orchestrator (multi-watcher process manager)
- Task Scheduler (Windows Task Scheduler)
- 8 skills total

### Gold (Autonomous Employee) ← Current
- Ralph Wiggum Stop Hook (autonomous loops)
- InstagramWatcher + FacebookWatcher
- TwitterWatcher
- Odoo MCP (accounting integration)
- Error recovery + graceful degradation in BaseWatcher
- 15 skills total
- Full architecture documentation

---

## Key Design Decisions

### 1. Obsidian as the Dashboard (not a web UI)
**Why:** Local-first, zero server costs, human-readable Markdown, git-trackable.
**Trade-off:** No real-time UI updates. We compensate with Dashboard.md updates after every action.

### 2. Playwright Browser UI (not REST APIs)
**Why LinkedIn/WhatsApp/Instagram:** REST APIs require app approval, business verification, or have strict rate limits. Browser automation works immediately with any account.
**Trade-off:** Session maintenance, bot detection risk, slower than API.
**Solution:** Persistent browser profiles (launch_persistent_context) save full session including IndexedDB (required for WhatsApp encryption keys).

### 3. Human-in-the-Loop via File System
**Why:** File movement is the most reliable, auditable approval mechanism.
- /Pending_Approval/ = "please review"
- /Approved/ = "execute this"
- /Done/ = "completed"
- /Rejected/ = "declined"

No database, no API calls — just files you can see and move in any file manager.

### 4. Ralph Wiggum Loop (Stop Hook)
**Why:** Claude Code exits after completing a prompt. For multi-step autonomous tasks, we need persistence.
**How:** The Stop hook intercepts exit, checks if the task file is in /Done, and re-injects the prompt if not.
**Completion detection:** File-movement based (task file moves to /Done) OR promise-based (Claude outputs TASK_COMPLETE).

### 5. Gmail: API + Browser Hybrid
**Gmail reading:** Google OAuth2 + Gmail API (fast, reliable, no bot detection).
**Gmail sending:** webbrowser.open() with pre-filled compose URL (avoids Google's Playwright bot detection).
**Why not full Playwright for Gmail:** Google's bot detection blocks headless browser login reliably.

---

## Watcher Pattern

All watchers follow the same pattern:

```python
class MyWatcher(BaseWatcher):
    def check_for_updates(self) -> list:
        # Poll the external source
        # Return list of new items

    def create_action_file(self, item) -> Path:
        # Write item to /Needs_Action/
        # Return file path

watcher = MyWatcher(vault_path="AI_Employee_Vault", check_interval=30)
watcher.run()  # Polls indefinitely with error recovery
```

BaseWatcher provides:
- Auto-retry with exponential backoff (5s, 15s, 30s, 60s, 120s)
- Graceful degradation (disables after 5 consecutive errors)
- Audit logging to /Logs/YYYY-MM-DD.json
- System alerts to /Needs_Action/ on failure

---

## Approval Workflow

```
External event (email/WhatsApp/scheduled)
    ↓
Watcher detects → creates WHATSAPP_*.md in /Needs_Action/
    ↓
Claude (/process-inbox) reads → drafts reply → creates APPROVAL_*.md in /Pending_Approval/
    ↓
Human reviews → moves file to /Approved/  (or /Rejected/)
    ↓
Claude (/approve-action or /send-email or /reply-whatsapp) reads /Approved/ → executes
    ↓
Result logged to /Logs/ → file moved to /Done/ → Dashboard.md updated
```

---

## Skills (Slash Commands)

| Skill | Tier | Purpose |
|-------|------|---------|
| /process-inbox | Bronze | Process all /Needs_Action items |
| /daily-briefing | Bronze | Morning status report |
| /check-vault | Bronze | Vault health check |
| /approve-action | Bronze | Execute /Approved items |
| /check-gmail | Silver | Poll Gmail, draft replies |
| /send-email | Silver | Send approved emails |
| /search-email | Silver | Search Gmail |
| /check-whatsapp | Silver | Scan WhatsApp messages |
| /reply-whatsapp | Silver | Send approved WA replies |
| /post-linkedin | Silver | Draft + publish LinkedIn |
| /draft-invoice | Silver | Generate invoice drafts |
| /weekly-audit | Silver | CEO briefing + audit |
| /ralph-loop | Gold | Autonomous task loops |
| /post-instagram | Gold | Instagram + Facebook posting |
| /post-twitter | Gold | Twitter/X posting |

---

## Lessons Learned

### 1. WhatsApp Web is Tricky
- `storage_state` (cookies/localStorage) is NOT enough — WhatsApp uses IndexedDB for encryption keys
- Solution: `launch_persistent_context(user_data_dir=...)` saves the full browser profile
- Chat input selector changes frequently — use JS evaluation by position (left > 400, top > 400) instead of CSS selectors
- Opening a chat: type search → `ArrowDown + Enter` (more reliable than clicking search results)

### 2. Google Blocks Playwright
- Gmail login via Playwright gets blocked by Google's bot detection
- Solution: webbrowser.open() with pre-filled compose URL — uses user's real Chrome session
- Gmail API works fine for reading (OAuth2 tokens persist with refresh)

### 3. LinkedIn Shadow DOM
- LinkedIn's post composer uses a Quill editor inside Shadow DOM
- `document.querySelectorAll('[contenteditable]')` finds nothing (doesn't pierce shadow DOM)
- Playwright's CSS locators pierce shadow DOM by default: `page.locator('.ql-editor')` works

### 4. File-Based Approval is Powerful
- Simple, auditable, works offline, visible in any file manager
- The Obsidian vault becomes the human's command center

### 5. Base Class Error Recovery
- Each watcher has different failure modes (browser crash, API token expiry, network timeout)
- Centralizing retry logic in BaseWatcher reduces code duplication
- Writing alerts to /Needs_Action/ ensures failures surface to the human operator

---

## Security Model

- Credentials stored in `config/` (gitignored)
- No credentials ever written to vault Markdown files
- All sensitive actions require human approval (file in /Approved/)
- Audit log in /Logs/ (90-day retention per Company_Handbook)
- Vault personal folders gitignored (/Done, /Logs, /Inbox, /Pending_Approval, /Approved, /Rejected, /Briefings, /Invoices, /Accounting)

---

*AI Employee v0.1 (Gold Tier) — Built for Personal AI Employee Hackathon 0, 2026*
