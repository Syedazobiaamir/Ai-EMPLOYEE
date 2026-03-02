# Personal AI Employee — Silver Tier

> **Hackathon:** Personal AI Employee Hackathon 0: Building Autonomous FTEs in 2026
> **Tier:** Silver (Functional Assistant)
> **Stack:** Claude Code + Obsidian + Python Watchers + Node.js MCP Server + Windows Task Scheduler

---

## Silver Tier Checklist

- [x] All Bronze requirements
- [x] **3 Watcher scripts**: Gmail + WhatsApp + LinkedIn (+ FileSystem from Bronze)
- [x] **Automatically post on LinkedIn** to generate sales (draft → approve → publish)
- [x] **Claude reasoning loop** that creates Plan.md files for multi-step tasks
- [x] **Email MCP server** (Node.js) for sending/drafting emails via Gmail API
- [x] **Human-in-the-loop** approval workflow for all sensitive actions
- [x] **Scheduling** via Windows Task Scheduler (8am briefing, 9am LinkedIn, Monday audit)
- [x] **All AI functionality** implemented as Agent Skills (7 slash commands)
- [x] **52 automated tests** passing (dry-run safe)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 PERCEPTION LAYER (Watchers)             │
│  FilesystemWatcher │ GmailWatcher │ WhatsAppWatcher     │
│                    │ LinkedInWatcher                    │
└────────────────────┬────────────────────────────────────┘
                     ↓ creates .md files
┌─────────────────────────────────────────────────────────┐
│              OBSIDIAN VAULT (Local Memory)              │
│  /Inbox → /Needs_Action → /Plans → /Pending_Approval   │
│                          ↓ human approves               │
│              /Approved → /Done  +  /Logs                │
└────────────────────┬────────────────────────────────────┘
                     ↓ reads & writes
┌─────────────────────────────────────────────────────────┐
│           REASONING LAYER (Claude Code)                 │
│  /process-inbox │ /daily-briefing │ /post-linkedin      │
│  /send-email    │ /approve-action │ /weekly-audit       │
│  /check-vault                                           │
└────────────────────┬────────────────────────────────────┘
                     ↓ MCP tools
┌─────────────────────────────────────────────────────────┐
│              ACTION LAYER (Email MCP Server)            │
│  send_email │ draft_email │ search_emails │ list_drafts │
└─────────────────────────────────────────────────────────┘
                     ↑ coordinates all
┌─────────────────────────────────────────────────────────┐
│              ORCHESTRATION LAYER                        │
│  orchestrator.py — starts watchers, watches /Approved   │
│  scheduler/setup_task_scheduler.py — Windows scheduling │
└─────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
hackathone ai employee fte/
├── CLAUDE.md                          ← Claude Code AI Employee rules (Silver)
├── README.md                          ← This file
├── orchestrator.py                    ← Master process (Silver)
├── AI_Employee_Vault/
│   ├── Dashboard.md
│   ├── Company_Handbook.md            ← Updated with LinkedIn rules
│   ├── Business_Goals.md
│   ├── Inbox/                         ← Drop files here
│   ├── Needs_Action/                  ← Watcher outputs + scheduled tasks
│   ├── Plans/                         ← Multi-step task plans
│   ├── Pending_Approval/              ← Awaiting human approval
│   ├── Approved/                      ← Move here to approve
│   ├── Rejected/                      ← Move here to reject
│   ├── Done/                          ← Completed items
│   ├── Logs/                          ← JSON audit logs
│   ├── Briefings/                     ← Generated briefings
│   ├── Invoices/                      ← Invoice files
│   └── Accounting/                    ← Financial records
├── watchers/
│   ├── base_watcher.py                ← Abstract base class
│   ├── filesystem_watcher.py          ← Bronze: file drop watcher
│   ├── gmail_watcher.py               ← Silver: Gmail API watcher
│   ├── whatsapp_watcher.py            ← Silver: WhatsApp Web watcher
│   ├── linkedin_watcher.py            ← Silver: LinkedIn watcher + poster
│   └── requirements.txt               ← Updated for Silver deps
├── mcp_servers/
│   └── email_mcp/
│       ├── index.js                   ← Email MCP server (Node.js)
│       └── package.json
├── scheduler/
│   └── setup_task_scheduler.py        ← Windows Task Scheduler setup
├── config/
│   └── .env.example                   ← Credential template (copy to .env)
├── tests/
│   └── test_silver.py                 ← 52-test Silver suite (dry-run safe)
└── .claude/
    └── commands/
        ├── process-inbox.md           ← Bronze
        ├── daily-briefing.md          ← Bronze
        ├── check-vault.md             ← Bronze
        ├── approve-action.md          ← Bronze
        ├── post-linkedin.md           ← Silver: LinkedIn workflow
        ├── send-email.md              ← Silver: Email via MCP
        └── weekly-audit.md            ← Silver: CEO briefing
```

---

## Setup Guide

### Step 1: Install Python Dependencies

```bash
pip install -r watchers/requirements.txt
playwright install chromium
```

### Step 2: Install Node.js MCP Server

```bash
cd mcp_servers/email_mcp
npm install
cd ../..
```

### Step 3: Configure Credentials

```bash
cp config/.env.example config/.env
# Edit config/.env with your real credentials
```

**Gmail Setup:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Gmail API
3. Create OAuth 2.0 Desktop credentials
4. Download as `config/gmail_credentials.json`
5. Run auth: `python watchers/gmail_watcher.py --vault AI_Employee_Vault --auth`

**LinkedIn Setup:**
1. Create a [LinkedIn App](https://www.linkedin.com/developers/apps)
2. Get access token with `w_member_social`, `r_liteprofile` permissions
3. Set `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_PERSON_URN` in `config/.env`

**WhatsApp Setup:**
1. Run: `python watchers/whatsapp_watcher.py --vault AI_Employee_Vault --no-headless`
2. Scan QR code in the browser window
3. Session saved to `config/whatsapp_session/` — never sync this to cloud

### Step 4: Configure MCP Server in Claude Code

Add to your Claude Code MCP config (`~/.claude/claude_code_config.json` or via `claude mcp add`):

```json
{
  "mcpServers": {
    "email": {
      "command": "node",
      "args": ["C:/absolute/path/to/mcp_servers/email_mcp/index.js"],
      "env": {
        "GMAIL_CREDENTIALS_PATH": "C:/absolute/path/to/config/gmail_credentials.json",
        "GMAIL_TOKEN_PATH": "C:/absolute/path/to/config/gmail_token.json",
        "VAULT_PATH": "C:/absolute/path/to/AI_Employee_Vault",
        "DRY_RUN": "false"
      }
    }
  }
}
```

### Step 5: Set Up Scheduling (Windows)

```bash
# Run as Administrator
python scheduler/setup_task_scheduler.py --vault AI_Employee_Vault --install

# Verify tasks
python scheduler/setup_task_scheduler.py --vault AI_Employee_Vault --list
```

This creates:
- **On login**: Orchestrator starts automatically
- **8:00 AM daily**: Daily briefing generated
- **9:00 AM daily**: LinkedIn post draft created
- **7:30 AM Monday**: Weekly CEO briefing

### Step 6: Run Tests

```bash
# All 52 tests, safe to run at any time (DRY_RUN mode)
python tests/test_silver.py --vault AI_Employee_Vault
```

### Step 7: Start the Orchestrator

```bash
# Start all watchers (skip Gmail/WhatsApp until credentials configured)
python orchestrator.py --vault AI_Employee_Vault --no-gmail --no-whatsapp

# Full mode (after credentials set up)
python orchestrator.py --vault AI_Employee_Vault

# Dry-run mode (safe testing)
python orchestrator.py --vault AI_Employee_Vault --dry-run
```

### Step 8: Open Claude Code

```bash
claude
```

---

## Agent Skills (Slash Commands)

| Command | Tier | Description |
|---------|------|-------------|
| `/process-inbox` | Bronze | Process all items in /Needs_Action |
| `/daily-briefing` | Bronze | Generate today's briefing report |
| `/check-vault` | Bronze | Health check on the vault |
| `/approve-action` | Bronze | Execute approved actions from /Approved |
| `/post-linkedin` | **Silver** | Draft or publish LinkedIn posts |
| `/send-email` | **Silver** | Draft or send emails via MCP |
| `/weekly-audit` | **Silver** | Weekly business audit + CEO briefing |

---

## The LinkedIn Workflow

```
LinkedIn Watcher (every 15min)
  → Detects business keyword in message
  → Creates: /Needs_Action/LINKEDIN_MSG_*.md
       ↓
  OR scheduled daily 9am:
  → Creates: /Needs_Action/LINKEDIN_POST_DRAFT_*.md
       ↓
Run /post-linkedin
  → Claude reads draft, presents options
       ↓
Human edits preferred option
  → Moves file to /Approved/
       ↓
Run /post-linkedin again
  → Orchestrator detects file in /Approved/
  → Calls: python watchers/linkedin_watcher.py --post-approved
  → Post published to LinkedIn
  → Logged to /Logs/ + moved to /Done/
```

---

## The Email Workflow

```
Gmail Watcher (every 2min)
  → Detects important unread email
  → Creates: /Needs_Action/EMAIL_*.md
       ↓
Run /process-inbox
  → Claude reads email, drafts reply
  → Creates: /Pending_Approval/APPROVAL_EMAIL_*.md
       ↓
Human reviews reply
  → Moves file to /Approved/
       ↓
Run /send-email
  → Claude calls email MCP tool: send_email(to, subject, body)
  → Email sent via Gmail API
  → Logged to /Logs/ + moved to /Done/
```

---

## Security

- Credentials **never** stored in vault Markdown files
- `config/.env` is in `.gitignore` (never committed)
- All actions logged to `/Logs/YYYY-MM-DD.json` (90-day retention)
- `DRY_RUN=true` by default — set to `false` only when ready for live
- Payments **always** require human approval, **never** auto-execute
- WhatsApp session stored locally only, never synced to cloud

---

## Tier Declaration

**Silver Tier** — Functional Assistant (20-30 hours estimated)

---

*Built for Panaversity AI Employee Hackathon 0, 2026*
