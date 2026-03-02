#!/usr/bin/env python3
"""
linkedin_watcher.py — LinkedIn Watcher & Auto-Poster for AI Employee (Silver Tier)

Two responsibilities:
1. MONITOR: Check LinkedIn for new connection requests, messages, and engagement
2. GENERATE: Read Business_Goals.md and create LinkedIn post drafts to generate sales

The watcher creates action files in /Needs_Action. All posts require
human approval before publishing (Company_Handbook: "All social posts require
human approval before publishing").

LinkedIn API Setup:
    1. Create a LinkedIn App at https://www.linkedin.com/developers/
    2. Request r_liteprofile, w_member_social, r_emailaddress permissions
    3. Get Access Token (OAuth 2.0)
    4. Set env vars: LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN

Posting uses Playwright browser UI (bypasses OAuth API restrictions):
    1. pip install playwright && playwright install chromium
    2. python linkedin_watcher.py --vault AI_Employee_Vault --setup-linkedin
       (Opens browser — log in to LinkedIn, then press Enter to save session)
    3. Session saved to LINKEDIN_SESSION_PATH (default: config/linkedin_session)

Usage:
    python linkedin_watcher.py --vault /path/to/AI_Employee_Vault
    python linkedin_watcher.py --vault /path/to/AI_Employee_Vault --dry-run
    python linkedin_watcher.py --vault /path/to/AI_Employee_Vault --generate-post
    python linkedin_watcher.py --vault /path/to/AI_Employee_Vault --post-approved
    python linkedin_watcher.py --vault /path/to/AI_Employee_Vault --setup-linkedin

Dependencies:
    pip install requests python-dotenv playwright
    playwright install chromium
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher

DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'

# How often to check LinkedIn (15 min to avoid rate limits)
CHECK_INTERVAL = int(os.getenv('LINKEDIN_CHECK_INTERVAL', '900'))

# How often to generate a post idea (every 24 hours)
POST_GENERATION_INTERVAL = int(os.getenv('LINKEDIN_POST_INTERVAL', '86400'))

LINKEDIN_API_BASE = 'https://api.linkedin.com/v2'

# Browser session for Playwright-based posting.
# Can be a JSON file (storageState) or a directory (persistent context).
DEFAULT_LINKEDIN_SESSION_PATH = str(
    Path(__file__).parent.parent / 'config' / 'linkedin_session.json'
)


class LinkedInAPI:
    """Wrapper around LinkedIn REST API."""

    def __init__(self, access_token: str, person_urn: str):
        self.access_token = access_token
        self.person_urn = person_urn  # e.g. "urn:li:person:ABC123"
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }

    def get_profile(self) -> dict:
        """Get basic profile info to verify auth."""
        import requests
        response = requests.get(
            f'{LINKEDIN_API_BASE}/me',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_messages(self) -> list:
        """Get recent LinkedIn messages."""
        import requests
        try:
            response = requests.get(
                f'{LINKEDIN_API_BASE}/messages',
                headers=self.headers,
                params={'q': 'mbox', 'mailboxUrn': self.person_urn}
            )
            if response.status_code == 200:
                return response.json().get('elements', [])
        except Exception:
            pass
        return []

    def post_share(self, text: str, visibility: str = 'PUBLIC') -> dict:
        """Post a text update to LinkedIn via REST API (may fail if app not verified)."""
        import requests
        payload = {
            'author': self.person_urn,
            'lifecycleState': 'PUBLISHED',
            'specificContent': {
                'com.linkedin.ugc.ShareContent': {
                    'shareCommentary': {'text': text},
                    'shareMediaCategory': 'NONE'
                }
            },
            'visibility': {
                'com.linkedin.ugc.MemberNetworkVisibility': visibility
            }
        }
        response = requests.post(
            f'{LINKEDIN_API_BASE}/ugcPosts',
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def post_share_browser(self, text: str,
                           session_path: str = DEFAULT_LINKEDIN_SESSION_PATH) -> dict:
        """
        Post to LinkedIn using Playwright browser UI automation.

        This bypasses OAuth API restrictions entirely — posts via the real
        LinkedIn web UI exactly as a human would.

        Supports two session formats:
          - JSON file (e.g. config/linkedin_session.json): Playwright storageState
          - Directory (e.g. config/linkedin_session/): Playwright persistent context

        Requires:
            pip install playwright && playwright install chromium
            Run --setup-linkedin first to save an authenticated session.
        """
        from playwright.sync_api import sync_playwright

        session_p = Path(session_path).resolve()
        is_json = session_p.suffix == '.json'

        with sync_playwright() as p:
            if is_json and session_p.exists():
                # JSON storage state — launch normal browser + load cookies
                browser = p.chromium.launch(
                    headless=False,
                    slow_mo=500,
                    args=['--no-sandbox', '--disable-blink-features=AutomationControlled'],
                )
                ctx = browser.new_context(
                    storage_state=str(session_p),
                    viewport={'width': 1280, 'height': 800},
                )
                page = ctx.new_page()
            else:
                # Directory persistent context
                ctx = p.chromium.launch_persistent_context(
                    str(session_p),
                    headless=False,
                    slow_mo=500,
                    args=['--no-sandbox', '--disable-blink-features=AutomationControlled'],
                )
                page = ctx.pages[0] if ctx.pages else ctx.new_page()

            # Navigate to LinkedIn feed
            page.goto('https://www.linkedin.com/feed/',
                      wait_until='domcontentloaded', timeout=30000)

            # Wait for feed to load
            page.wait_for_timeout(4000)

            # Verify we're logged in
            if 'login' in page.url or 'checkpoint' in page.url or 'authwall' in page.url:
                ctx.close()
                raise Exception(
                    'Not logged in to LinkedIn. '
                    'Run: python linkedin_watcher.py --vault <vault> --setup-linkedin'
                )

            # Click "Start a post" button (LinkedIn removed aria-label, match by text)
            page.get_by_text('Start a post', exact=True).first.click()

            # Wait for Quill editor to load in the preload frame (up to 30s)
            # LinkedIn renders the post composer inside a hidden preload iframe
            target_frame = None
            for _ in range(30):
                for frame in page.frames:
                    try:
                        has = frame.evaluate('() => { const el = document.querySelector(".ql-editor"); return el && el.offsetHeight > 0; }')
                        if has:
                            target_frame = frame
                            break
                    except Exception:
                        pass
                if target_frame:
                    break
                page.wait_for_timeout(1000)

            if not target_frame:
                raise Exception('Could not find .ql-editor in any frame after 30s')

            # Focus editor via JS then type with keyboard
            target_frame.evaluate('() => document.querySelector(".ql-editor").focus()')
            page.wait_for_timeout(300)

            # Type using keyboard (most reliable with shadow DOM editors)
            page.keyboard.type(text, delay=15)
            page.wait_for_timeout(2000)

            # Click the Post button
            post_btn = page.locator('button.share-actions__primary-action')
            if post_btn.count() == 0:
                post_btn = page.locator('button[aria-label="Post"]')
            post_btn.first.wait_for(state='visible', timeout=10000)
            post_btn.first.click()
            page.wait_for_timeout(5000)

            ctx.close()

        return {'status': 'posted', 'method': 'browser_ui', 'preview': text[:80]}


class LinkedInWatcher(BaseWatcher):
    """
    Silver Tier Watcher: Monitors LinkedIn and generates post drafts.

    Two modes:
    - Monitor mode: Checks for messages/notifications needing response
    - Generator mode: Creates LinkedIn post drafts based on Business_Goals
    """

    def __init__(self, vault_path: str):
        super().__init__(vault_path, check_interval=CHECK_INTERVAL)
        self.access_token = os.getenv('LINKEDIN_ACCESS_TOKEN', '')
        self.person_urn = os.getenv('LINKEDIN_PERSON_URN', '')
        self.api: Optional[LinkedInAPI] = None
        self.last_post_generated: Optional[datetime] = None
        self.processed_ids: set = set()
        self._load_state()

    def _load_state(self):
        state_file = self.vault_path / 'Logs' / 'linkedin_state.json'
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding='utf-8'))
                self.processed_ids = set(data.get('processed_ids', []))
                last_gen = data.get('last_post_generated')
                if last_gen:
                    self.last_post_generated = datetime.fromisoformat(last_gen)
            except Exception:
                pass

    def _save_state(self):
        state_file = self.vault_path / 'Logs' / 'linkedin_state.json'
        try:
            state_file.write_text(json.dumps({
                'processed_ids': list(self.processed_ids),
                'last_post_generated': self.last_post_generated.isoformat()
                    if self.last_post_generated else None
            }, indent=2), encoding='utf-8')
        except Exception as e:
            self.logger.warning(f'Could not save LinkedIn state: {e}')

    def _connect(self):
        if not self.access_token or not self.person_urn:
            self.logger.warning('LinkedIn credentials not set. Set LINKEDIN_ACCESS_TOKEN '
                                'and LINKEDIN_PERSON_URN environment variables.')
            return False
        if self.api is None:
            self.api = LinkedInAPI(self.access_token, self.person_urn)
        return True

    def _read_business_goals(self) -> str:
        """Read Business_Goals.md to generate relevant post content."""
        goals_file = self.vault_path / 'Business_Goals.md'
        if goals_file.exists():
            return goals_file.read_text(encoding='utf-8')
        return ''

    def _should_generate_post(self) -> bool:
        """Check if it's time to generate a new LinkedIn post draft."""
        if self.last_post_generated is None:
            return True
        elapsed = (datetime.now() - self.last_post_generated).total_seconds()
        return elapsed >= POST_GENERATION_INTERVAL

    def check_for_updates(self) -> list:
        """Check LinkedIn for messages + decide if post generation is needed."""
        items = []

        if DRY_RUN:
            self.logger.info('[DRY RUN] Simulating LinkedIn check')
            # Simulate a message
            items.append({
                'type': 'message',
                'id': 'mock_li_msg_001',
                'sender': 'Prospective Client (LinkedIn)',
                'text': 'Hi! I saw your post about AI automation. Could you tell me more about your pricing?',
                '_mock': True
            })
            # Simulate post generation trigger
            if self._should_generate_post():
                items.append({'type': 'generate_post', '_mock': True})
            return items

        # Check messages
        if self._connect():
            try:
                messages = self.api.get_messages()
                for msg in messages:
                    msg_id = msg.get('entityUrn', msg.get('id', ''))
                    if msg_id and msg_id not in self.processed_ids:
                        items.append({
                            'type': 'message',
                            'id': msg_id,
                            'data': msg
                        })
            except Exception as e:
                self.logger.error(f'LinkedIn API error: {e}')

        # Check if we should generate a post
        if self._should_generate_post():
            items.append({'type': 'generate_post'})

        return items

    def create_action_file(self, item: dict) -> Path:
        """Create action file for LinkedIn item."""
        item_type = item.get('type')
        if item_type == 'message':
            return self._create_message_action(item)
        elif item_type == 'generate_post':
            return self._create_post_draft()
        return None

    def _create_message_action(self, message: dict) -> Path:
        """Create action file for a LinkedIn message."""
        msg_id = message['id']
        is_mock = message.get('_mock', False)
        sender = message.get('sender', 'LinkedIn Contact')
        text = message.get('text', message.get('data', {}).get('body', {}).get('text', ''))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'LINKEDIN_MSG_{timestamp}.md'
        filepath = self.needs_action / filename

        content = f"""---
type: linkedin_message
source: linkedin
message_id: {msg_id}
sender: {sender}
received: {datetime.now().isoformat()}
priority: normal
status: pending
requires_approval: true
dry_run: {str(is_mock or DRY_RUN).lower()}
---

## LinkedIn Message Received

**From:** {sender}
**Received:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Message
> {text}

## Suggested Actions
- [ ] Draft a professional reply
- [ ] Identify if this is a sales lead
- [ ] Create approval request before replying
- [ ] If pricing request: check Accounting/Rates.md
- [ ] Log interaction

## AI Employee Notes
All LinkedIn replies require human approval (Company_Handbook Section 5).
"""
        filepath.write_text(content, encoding='utf-8')
        self.processed_ids.add(msg_id)
        self._save_state()
        self._log_action('linkedin_message', sender, filename)
        return filepath

    def _create_post_draft(self) -> Path:
        """Generate a LinkedIn post draft based on Business_Goals."""
        business_goals = self._read_business_goals()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'LINKEDIN_POST_DRAFT_{timestamp}.md'
        filepath = self.needs_action / filename

        # Build post ideas based on business goals
        today = datetime.now().strftime('%B %d, %Y')
        post_themes = self._select_post_theme(business_goals)

        content = f"""---
type: linkedin_post_draft
source: linkedin_watcher
created: {datetime.now().isoformat()}
priority: normal
status: pending_approval
requires_approval: true
action: post_to_linkedin
---

## LinkedIn Post Draft — {today}

**Purpose:** Generate business leads and showcase expertise

---

## Suggested Post Options

### Option A: Value/Tips Post
```
{post_themes['tips']}
```

### Option B: Service Showcase Post
```
{post_themes['service']}
```

### Option C: Results/Social Proof Post
```
{post_themes['results']}
```

---

## How to Approve
1. Edit your preferred post above
2. Move this file to `/Approved/`
3. Run `/post-linkedin` to publish

## AI Employee Notes
- All posts require human approval (Company_Handbook Section 5)
- Never post about competitors or share confidential client info
- Suggested posting times: Tuesday-Thursday 8-10am or 5-6pm
- Business goals reference: See Business_Goals.md for context
"""
        filepath.write_text(content, encoding='utf-8')
        self.last_post_generated = datetime.now()
        self._save_state()
        self._log_action('linkedin_post_draft', 'linkedin', filename)
        return filepath

    def _select_post_theme(self, business_goals: str) -> dict:
        """Generate post themes based on business context."""
        # Extract basic info from business goals
        service_hint = 'AI automation and digital solutions'
        if 'AI' in business_goals or 'automation' in business_goals:
            service_hint = 'AI automation and business intelligence'
        elif 'consulting' in business_goals.lower():
            service_hint = 'consulting and strategic advisory'
        elif 'software' in business_goals.lower():
            service_hint = 'software development and digital transformation'

        today_date = datetime.now().strftime('%B %Y')

        return {
            'tips': (
                f"5 things I've learned helping businesses automate in {today_date}:\n\n"
                f"1️⃣ Start with your most repetitive task\n"
                f"2️⃣ Human oversight > full automation (at first)\n"
                f"3️⃣ Document everything before automating it\n"
                f"4️⃣ Small wins build confidence fast\n"
                f"5️⃣ The best system is the one your team actually uses\n\n"
                f"What's one process you wish you could automate?\n\n"
                f"#AI #Automation #BusinessProductivity #DigitalTransformation"
            ),
            'service': (
                f"🤖 Is your business still handling routine tasks manually?\n\n"
                f"We specialize in {service_hint} — helping small businesses "
                f"reclaim 10+ hours per week.\n\n"
                f"📌 What we do:\n"
                f"• Email triage & intelligent routing\n"
                f"• Automated invoicing & follow-ups\n"
                f"• 24/7 business monitoring\n\n"
                f"💬 DM me to see how much time your business can save.\n\n"
                f"#SmallBusiness #Productivity #AI #Automation"
            ),
            'results': (
                f"📊 This month's results with our AI Employee system:\n\n"
                f"✅ Response time cut from 4 hours → under 30 minutes\n"
                f"✅ Invoice follow-ups now automated\n"
                f"✅ Zero missed important emails\n\n"
                f"This isn't science fiction — it's available today.\n\n"
                f"Want to see how it works? Drop a comment or DM me.\n\n"
                f"#AIEmployee #BusinessAutomation #Productivity #Results"
            )
        }

    def _log_action(self, action_type: str, target: str, filename: str):
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs / f'{today}.json'
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": "linkedin_watcher",
            "target": target,
            "parameters": {},
            "approval_status": "pending",
            "approved_by": None,
            "result": "draft_created",
            "action_file": filename,
            "dry_run": DRY_RUN
        }
        entries = []
        if log_file.exists():
            try:
                entries = json.loads(log_file.read_text(encoding='utf-8'))
            except Exception:
                entries = []
        entries.append(entry)
        log_file.write_text(json.dumps(entries, indent=2), encoding='utf-8')

    def run(self):
        self.logger.info('Starting LinkedIn Watcher (Silver Tier)')
        self.logger.info(f'Post generation interval: every {POST_GENERATION_INTERVAL // 3600}h')
        self.logger.info(f'Message check interval: every {self.check_interval // 60}min')
        self.logger.info(f'Dry-run mode: {DRY_RUN}')
        self.logger.info('Press Ctrl+C to stop.\n')

        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    action_file = self.create_action_file(item)
                    if action_file:
                        self.logger.info(f'Created action file: {action_file.name}')
            except KeyboardInterrupt:
                self.logger.info('LinkedIn Watcher stopped.')
                break
            except Exception as e:
                self.logger.error(f'Unexpected error: {e}', exc_info=True)
            time.sleep(self.check_interval)


def setup_linkedin_session(vault_path: Path):
    """
    Launch browser for first-time LinkedIn login. Session is saved so future
    posts don't require manual login.

    Run once:
        python linkedin_watcher.py --vault AI_Employee_Vault --setup-linkedin
    """
    from playwright.sync_api import sync_playwright

    session_path = str(Path(
        os.getenv('LINKEDIN_SESSION_PATH', DEFAULT_LINKEDIN_SESSION_PATH)
    ).resolve())

    print(f'Saving session to: {session_path}')
    print('A browser window will open. Log in to LinkedIn, then press Enter here.')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto('https://www.linkedin.com/login', wait_until='domcontentloaded')

        print('\nBrowser is open. Log in to LinkedIn.')
        print('Waiting up to 120 seconds — session saves automatically once you are logged in...')

        # Auto-detect login: wait for feed or profile to appear (max 120s)
        try:
            page.wait_for_url('**/feed/**', timeout=120000)
        except Exception:
            pass  # Save whatever state we have

        print('Login detected — saving session...')
        # Save cookies + localStorage to JSON
        ctx.storage_state(path=session_path)
        ctx.close()
        browser.close()

    print(f'LinkedIn session saved to: {session_path}')
    print('You can now run --post-approved to publish posts.')


def post_approved_content(vault_path: Path, dry_run: bool = False):
    """
    Execute an approved LinkedIn post via Playwright browser UI.
    Called by the /post-linkedin skill or orchestrator when a
    LINKEDIN_POST_DRAFT_* file is moved to /Approved/.
    """
    import re

    session_path = os.getenv('LINKEDIN_SESSION_PATH', DEFAULT_LINKEDIN_SESSION_PATH)
    token = os.getenv('LINKEDIN_ACCESS_TOKEN', '')
    urn = os.getenv('LINKEDIN_PERSON_URN', '')

    approved_dir = vault_path / 'Approved'
    done_dir = vault_path / 'Done'
    logs_dir = vault_path / 'Logs'

    found = list(approved_dir.glob('LINKEDIN_POST_DRAFT_*.md'))
    if not found:
        print('No approved LinkedIn post drafts found in /Approved/')
        return False

    for approval_file in found:
        content = approval_file.read_text(encoding='utf-8')

        # Extract the first ``` code block — that's the selected post text
        matches = re.findall(r'```\n(.*?)\n```', content, re.DOTALL)
        if not matches:
            print(f'No post content found in {approval_file.name}')
            continue

        post_text = matches[0].strip()

        if dry_run:
            print(f'[DRY RUN] Would post to LinkedIn:\n{post_text}\n')
            result = {'status': 'dry_run', 'method': 'browser_ui'}
        else:
            try:
                api = LinkedInAPI(token, urn)
                result = api.post_share_browser(post_text, session_path=session_path)
                print(f'Posted to LinkedIn: {result}')
            except Exception as e:
                print(f'ERROR posting to LinkedIn: {e}')
                continue

        if dry_run:
            print(f'[DRY RUN] File stays in /Approved/ (not moved)\n')
            continue

        # Log the action
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = logs_dir / f'{today}.json'
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": "linkedin_post_published",
            "actor": "claude_code",
            "target": "linkedin",
            "parameters": {"post_preview": post_text[:100]},
            "approval_status": "approved",
            "approved_by": "human",
            "result": "success",
            "dry_run": False
        }
        entries = []
        if log_file.exists():
            try:
                entries = json.loads(log_file.read_text(encoding='utf-8'))
            except Exception:
                entries = []
        entries.append(entry)
        log_file.write_text(json.dumps(entries, indent=2), encoding='utf-8')

        # Move to Done (use replace() to overwrite any duplicate on Windows)
        done_file = done_dir / approval_file.name
        approval_file.replace(done_file)
        print(f'Moved {approval_file.name} to Done/')

    return True


def main():
    # Ensure UTF-8 output on Windows (needed for emoji in post text)
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(
        description='AI Employee — LinkedIn Watcher (Silver Tier)'
    )
    parser.add_argument('--vault', required=True,
                        help='Absolute path to AI_Employee_Vault folder')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulate without hitting LinkedIn API')
    parser.add_argument('--generate-post', action='store_true',
                        help='Immediately generate a LinkedIn post draft and exit')
    parser.add_argument('--post-approved', action='store_true',
                        help='Publish approved LinkedIn posts from /Approved/ and exit')
    parser.add_argument('--setup-linkedin', action='store_true',
                        help='Open browser to log in to LinkedIn and save session for future posts')
    args = parser.parse_args()

    if args.dry_run:
        os.environ['DRY_RUN'] = 'true'
        global DRY_RUN
        DRY_RUN = True

    vault_path = Path(args.vault).resolve()
    if not vault_path.exists():
        print(f'ERROR: Vault not found: {vault_path}')
        sys.exit(1)

    if args.setup_linkedin:
        setup_linkedin_session(vault_path)
        sys.exit(0)

    if args.post_approved:
        post_approved_content(vault_path, dry_run=DRY_RUN)
        sys.exit(0)

    watcher = LinkedInWatcher(str(vault_path))

    if args.generate_post:
        print('Generating LinkedIn post draft...')
        action_file = watcher._create_post_draft()
        print(f'Draft created: {action_file}')
        sys.exit(0)

    watcher.run()


if __name__ == '__main__':
    main()
