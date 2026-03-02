#!/usr/bin/env python3
"""
whatsapp_watcher.py — WhatsApp Watcher for AI Employee (Silver Tier)

Uses Playwright to monitor WhatsApp Web for unread messages containing
business keywords (urgent, invoice, payment, etc.).
Creates action .md files in /Needs_Action for Claude to process.

IMPORTANT: WhatsApp session is stored locally. Never sync the session
directory to the cloud — it contains your WhatsApp credentials.

Setup:
    1. pip install playwright
    2. playwright install chromium
    3. First run will open WhatsApp Web — scan QR code to authenticate
    4. Session is saved in config/whatsapp_session/

Usage:
    python whatsapp_watcher.py --vault /path/to/AI_Employee_Vault
    python whatsapp_watcher.py --vault /path/to/AI_Employee_Vault --dry-run
    python whatsapp_watcher.py --vault /path/to/AI_Employee_Vault --headless

Dependencies:
    pip install playwright
    playwright install chromium
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher

DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'

# Keywords that flag a WhatsApp message as needing AI Employee attention
PRIORITY_KEYWORDS = [
    # Greetings
    'hi', 'hello', 'hey', 'salam', 'assalam', 'assalamualaikum', 'aoa',
    # Business
    'urgent', 'asap', 'invoice', 'payment', 'pay', 'overdue',
    'help', 'price', 'pricing', 'quote', 'proposal', 'contract',
    'deadline', 'meeting', 'call', 'important', 'emergency'
]

DEFAULT_SESSION_PATH = Path(__file__).parent.parent / 'config' / 'whatsapp_session'


class WhatsAppWatcher(BaseWatcher):
    """
    Silver Tier Watcher: Monitors WhatsApp Web via Playwright automation.
    Polls every 30 seconds.

    NOTE: This respects WhatsApp's usage — it only reads, never sends
    messages autonomously. All replies go through the HITL approval flow.
    """

    def __init__(self, vault_path: str, session_path: Path = DEFAULT_SESSION_PATH,
                 headless: bool = True):
        super().__init__(vault_path, check_interval=30)
        self.session_path = session_path
        self.headless = headless
        self.processed_message_ids: set = set()
        self._load_processed_ids()
        # Persistent browser — opened once, reused every poll
        self._playwright = None
        self._browser = None
        self._page = None

    def _load_processed_ids(self):
        state_file = self.vault_path / 'Logs' / 'whatsapp_processed.json'
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding='utf-8'))
                self.processed_message_ids = set(data.get('processed_ids', []))
                self.logger.info(f'Loaded {len(self.processed_message_ids)} processed WhatsApp IDs')
            except Exception:
                pass

    def _save_processed_ids(self):
        state_file = self.vault_path / 'Logs' / 'whatsapp_processed.json'
        try:
            state_file.write_text(
                json.dumps({'processed_ids': list(self.processed_message_ids)}, indent=2),
                encoding='utf-8'
            )
        except Exception as e:
            self.logger.warning(f'Could not save WhatsApp processed IDs: {e}')

    def _start_browser(self):
        """Open persistent browser profile and navigate to WhatsApp Web."""
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

        self._playwright = sync_playwright().start()
        profile_dir = WHATSAPP_PROFILE_DIR
        profile_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f'Using persistent profile: {profile_dir}')

        ctx = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=self.headless,
            slow_mo=200,
            args=_BROWSER_ARGS,
            ignore_default_args=['--enable-automation'],
            viewport={'width': 1280, 'height': 800},
            user_agent=_USER_AGENT,
        )
        ctx.add_init_script(_INIT_SCRIPT)
        self._browser = ctx  # store context as _browser for _stop_browser
        self._page = ctx.pages[0] if ctx.pages else ctx.new_page()
        self._page.goto('https://web.whatsapp.com')

        QR_SELECTORS = 'canvas[aria-label*="QR"], [data-ref], [data-testid="qrcode"]'

        try:
            self._page.wait_for_selector(
                f'{_CHAT_LIST}, {QR_SELECTORS}',
                timeout=30000
            )
        except PlaywrightTimeout:
            self.logger.warning('WhatsApp Web timed out loading.')
            return False

        qr = self._page.query_selector(QR_SELECTORS)
        if qr:
            self.logger.warning('QR code detected — scan with your phone.')
            try:
                self._page.wait_for_selector(_CHAT_LIST, timeout=180000)
                self.logger.info('QR scan successful — WhatsApp Web loaded.')
            except PlaywrightTimeout:
                self.logger.error('QR scan timed out.')
                return False

        self.logger.info('Browser connected to WhatsApp Web. Polling every 30s...')
        return True

    def _stop_browser(self):
        """Clean up browser resources."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._page = None
        self._playwright = None

    def run(self):
        """Override run to keep browser open across all poll cycles."""
        self.logger.info('Starting WhatsApp Watcher (Silver Tier)')
        self.logger.info(f'Session stored at: {self.session_path}')
        self.logger.info(f'Headless mode: {self.headless}')
        self.logger.info(f'Dry-run mode: {DRY_RUN}')
        self.logger.info(f'Polling every {self.check_interval}s')
        self.logger.info(f'Monitoring keywords: {", ".join(PRIORITY_KEYWORDS)}')
        self.logger.info('Press Ctrl+C to stop.')

        if not DRY_RUN:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                self.logger.error('Playwright not installed.')
                return
            if not self._start_browser():
                self.logger.error('Failed to connect to WhatsApp Web. Exiting.')
                return

        try:
            while True:
                try:
                    items = self.check_for_updates()
                    for item in items:
                        action_file = self.create_action_file(item)
                        self.logger.info(f'Created action file: {action_file}')
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    self.logger.error(f'Poll error: {e}')
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.logger.info('Watcher stopped by user.')
        finally:
            self._stop_browser()

    def check_for_updates(self) -> list:
        """Scan the already-open WhatsApp Web page for unread messages."""
        if DRY_RUN:
            self.logger.info('[DRY RUN] Simulating WhatsApp check — returning mock message')
            return [{
                'id': 'mock_wa_001',
                'sender': 'Client A (+1-555-0100)',
                'text': 'Hi, can you send me the invoice for the January project? Urgent!',
                'time': datetime.now().strftime('%H:%M'),
                '_mock': True
            }]

        if not self._page:
            self.logger.warning('Browser not open. Skipping poll.')
            return []

        messages = []
        try:
            # Get all text from the chat list pane — works regardless of WhatsApp Web's internal selectors
            pane_text = ''
            for selector in ['#pane-side', 'div[aria-label="Chat list"]', '[data-testid="chat-list"]', 'body']:
                try:
                    el = self._page.query_selector(selector)
                    if el:
                        pane_text = el.inner_text()
                        self.logger.debug(f'Read chat list via selector: {selector} ({len(pane_text)} chars)')
                        break
                except Exception:
                    continue

            if not pane_text:
                self.logger.debug('No chat list text found this poll.')
                return []

            # Scan lines for keyword matches
            lines = pane_text.splitlines()
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                if not line_lower:
                    continue
                matched_keywords = [kw for kw in PRIORITY_KEYWORDS if kw in line_lower]
                if matched_keywords:
                    # Use surrounding lines as context (sender name often 1-2 lines above)
                    context_start = max(0, i - 2)
                    sender = lines[context_start].strip() or 'Unknown'
                    msg_id = f'wa_{sender[:30]}_{datetime.now().strftime("%Y%m%d")}'
                    if msg_id not in self.processed_message_ids:
                        messages.append({
                            'id': msg_id,
                            'sender': sender,
                            'text': line.strip(),
                            'keywords': matched_keywords,
                            'time': datetime.now().strftime('%H:%M')
                        })
                        self.processed_message_ids.add(msg_id)

        except Exception as e:
            self.logger.error(f'WhatsApp poll error: {e}')

        if messages:
            self.logger.info(f'Found {len(messages)} message(s) needing attention')
            self._save_processed_ids()
        return messages

    def create_action_file(self, message: dict) -> Path:
        """Create a Needs_Action .md file for a WhatsApp message."""
        msg_id = message['id']
        sender = message['sender']
        text = message['text']
        keywords = message.get('keywords', [])
        msg_time = message.get('time', datetime.now().strftime('%H:%M'))
        is_mock = message.get('_mock', False)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'WHATSAPP_{timestamp}_{msg_id[:12].replace("/", "_")}.md'
        filepath = self.needs_action / filename

        # Classify action type
        GREETING_KWS = {'hi', 'hello', 'hey', 'salam', 'assalam', 'assalamualaikum', 'aoa'}
        if any(kw in GREETING_KWS for kw in keywords):
            action_type = 'greeting'
            suggested_actions = [
                '- [ ] Reply with a warm welcome message',
                '- [ ] Introduce services briefly',
                '- [ ] Create approval request before sending'
            ]
        elif any(kw in ['invoice', 'payment', 'pay', 'quote', 'pricing', 'price'] for kw in keywords):
            action_type = 'billing_request'
            suggested_actions = [
                '- [ ] Draft invoice or quote',
                '- [ ] Create approval request for email send',
                '- [ ] Check Accounting/Rates.md for pricing'
            ]
        elif any(kw in ['meeting', 'call'] for kw in keywords):
            action_type = 'meeting_request'
            suggested_actions = [
                '- [ ] Check calendar availability',
                '- [ ] Draft meeting confirmation reply',
                '- [ ] Create approval request before replying'
            ]
        else:
            action_type = 'general_inquiry'
            suggested_actions = [
                '- [ ] Draft a reply to the sender',
                '- [ ] Create approval request before sending',
                '- [ ] Update Dashboard with interaction'
            ]

        content = f"""---
type: whatsapp_message
source: whatsapp
message_id: {msg_id}
sender: {sender}
received: {datetime.now().isoformat()}
message_time: {msg_time}
priority: high
action_type: {action_type}
keywords_matched: {', '.join(keywords)}
status: pending
dry_run: {str(is_mock or DRY_RUN).lower()}
---

## WhatsApp Message Received

**From:** {sender}
**Time:** {msg_time}
**Keywords Detected:** {', '.join(keywords) if keywords else 'none'}

## Message Content
> {text}

## Suggested Actions
{chr(10).join(suggested_actions)}
- [ ] Log interaction to /Logs/

## AI Employee Notes
This message contains business keywords requiring attention.
Per Company_Handbook: flag urgent payment requests and complaints for human review.
**All replies require human approval before sending.**
"""

        filepath.write_text(content, encoding='utf-8')
        self.processed_message_ids.add(msg_id)
        self._save_processed_ids()
        self._log_action(msg_id, sender, text[:100], filename)

        return filepath

    def _log_action(self, msg_id: str, sender: str, preview: str, filename: str):
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs / f'{today}.json'
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": "whatsapp_message_detected",
            "actor": "whatsapp_watcher",
            "target": sender,
            "parameters": {"preview": preview, "message_id": msg_id},
            "approval_status": "auto",
            "approved_by": "system",
            "result": "success",
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

WHATSAPP_PROFILE_DIR = Path(__file__).parent.parent / 'config' / 'whatsapp_profile'

_BROWSER_ARGS = [
    '--no-sandbox',
    '--disable-blink-features=AutomationControlled',
    '--window-size=1280,800',
    '--window-position=100,50',
]
_INIT_SCRIPT = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/122.0.0.0 Safari/537.36'
)
_CHAT_LIST = '#pane-side, [data-testid="chat-list"], div[aria-label="Chat list"]'


def setup_whatsapp_session(profile_dir: Path = WHATSAPP_PROFILE_DIR):
    """Open a persistent browser profile, scan QR code, then close — session persists on disk."""
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    profile_dir.mkdir(parents=True, exist_ok=True)
    print('Opening WhatsApp Web with persistent profile. Scan the QR code with your phone.')
    print(f'Profile stored at: {profile_dir}')

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            slow_mo=300,
            args=_BROWSER_ARGS,
            ignore_default_args=['--enable-automation'],
            viewport={'width': 1280, 'height': 800},
            user_agent=_USER_AGENT,
        )
        ctx.add_init_script(_INIT_SCRIPT)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto('https://web.whatsapp.com')

        print('Waiting for QR scan (up to 3 minutes)...')
        try:
            page.wait_for_selector(_CHAT_LIST, timeout=180000)
            print('Logged in! Profile saved. You can now use --reply-approved.')
        except PlaywrightTimeout:
            print('ERROR: QR scan timed out. Please try again.')
        finally:
            ctx.close()


def send_reply_browser(sender_name: str, reply_text: str,
                       profile_dir: Path = WHATSAPP_PROFILE_DIR) -> dict:
    """Open WhatsApp Web using the persistent profile, find the chat, and send the reply."""
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    print(f'\nOpening WhatsApp Web → replying to: {sender_name}')

    if not profile_dir.exists():
        print(f'WARNING: No profile at {profile_dir}. Run --setup-whatsapp first.')

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            slow_mo=500,
            args=_BROWSER_ARGS,
            ignore_default_args=['--enable-automation'],
            viewport={'width': 1280, 'height': 800},
            user_agent=_USER_AGENT,
        )
        ctx.add_init_script(_INIT_SCRIPT)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        try:
            page.goto('https://web.whatsapp.com')
            page.wait_for_selector(_CHAT_LIST, timeout=30000)
            print('WhatsApp Web loaded.')

            # Click the search input and type the contact name
            search_term = sender_name.split(',')[0].strip()
            search_input = page.locator('div[aria-label="Search input textbox"]')
            search_input.wait_for(state='visible', timeout=10000)
            search_input.click()
            page.wait_for_timeout(500)
            page.keyboard.type(search_term)
            print(f'Searching for: {search_term}')

            # Wait for results then use ArrowDown + Enter to open the first hit
            page.wait_for_timeout(2500)
            page.keyboard.press('ArrowDown')
            page.wait_for_timeout(300)
            page.keyboard.press('Enter')
            print('Opened chat.')

            # Wait for the conversation panel to render the compose box
            page.wait_for_timeout(3000)

            # Wait for compose area to load after chat opens
            page.wait_for_timeout(3000)
            # Find message input via JS: right-hand pane only (left > 400px), skip search box
            focused = page.evaluate("""
                () => {
                    const candidates = document.querySelectorAll('[contenteditable="true"]');
                    const info = [];
                    let best = null;
                    for (const el of candidates) {
                        const rect = el.getBoundingClientRect();
                        const label = (el.getAttribute('aria-label') || '').toLowerCase();
                        info.push(label + ' top=' + Math.round(rect.top) + ' left=' + Math.round(rect.left));
                        // Compose box is in the right panel (left > 400) and near the bottom (top > 400)
                        if (rect.left > 400 && rect.top > 400 && rect.height > 10) {
                            best = el;
                            break;
                        }
                    }
                    window._wa_debug = info.join(' | ');
                    if (best) { best.click(); best.focus(); return best.outerHTML.slice(0, 120); }
                    return null;
                }
            """)
            debug_info = page.evaluate("() => window._wa_debug || ''")
            print(f'Contenteditable elements: {debug_info}')
            print(f'Message input found: {focused is not None} — {str(focused)[:80]}')
            if not focused:
                raise Exception('Could not locate message input box via JS')

            page.keyboard.type(reply_text)
            page.wait_for_timeout(500)
            page.keyboard.press('Enter')
            print('Reply sent!')
            page.wait_for_timeout(3000)

            return {'status': 'sent', 'method': 'browser_ui', 'sender': sender_name}

        except PlaywrightTimeout as e:
            print(f'Timeout: {e}')
            return {'status': 'error', 'method': 'browser_ui', 'error': str(e)}
        except Exception as e:
            print(f'Error: {e}')
            return {'status': 'error', 'method': 'browser_ui', 'error': str(e)}
        finally:
            page.wait_for_timeout(2000)
            ctx.close()


def send_approved_replies(vault_path: Path, dry_run: bool = False,
                          profile_dir: Path = WHATSAPP_PROFILE_DIR):
    """Send all approved APPROVAL_WHATSAPP_*.md reply files from /Approved/ via browser UI."""
    import re

    approved_dir = vault_path / 'Approved'
    done_dir = vault_path / 'Done'
    logs_dir = vault_path / 'Logs'

    found = list(approved_dir.glob('APPROVAL_WHATSAPP_*.md'))
    if not found:
        print('No approved WhatsApp reply files found in /Approved/')
        return False

    for approval_file in found:
        content = approval_file.read_text(encoding='utf-8')

        # Find all ### Message N sections
        sections = re.findall(
            r'###\s+Message\s+\d+[^\n]*\n(.*?)(?=###\s+Message|\Z)',
            content, re.DOTALL
        )

        if not sections:
            print(f'No message sections found in {approval_file.name}')
            continue

        results = []
        for section in sections:
            from_match = re.search(r'\*\*From:\*\*\s*(.+)', section)
            sender = from_match.group(1).strip() if from_match else 'Unknown'

            # Extract > quoted reply lines
            reply_lines = re.findall(r'^>\s*(.+)', section, re.MULTILINE)
            reply_text = '\n'.join(reply_lines).strip()

            if not reply_text:
                print(f'No reply text found for: {sender} — skipping')
                continue

            print(f'\nApproved WhatsApp reply:')
            print(f'  To:      {sender}')
            print(f'  Preview: {reply_text[:80]}')

            if dry_run:
                print('[DRY RUN] Would send via WhatsApp browser.')
                results.append({'status': 'dry_run', 'sender': sender})
                continue

            result = send_reply_browser(sender, reply_text, profile_dir)
            results.append(result)
            print(f'Result: {result}')

        if dry_run:
            continue

        # Log
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = logs_dir / f'{today}.json'
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": "whatsapp_replies_sent_browser",
            "actor": "whatsapp_watcher",
            "target": "multiple_contacts",
            "parameters": {"results": results, "method": "browser_ui"},
            "approval_status": "approved",
            "approved_by": "human",
            "result": "success",
            "dry_run": False,
        }
        entries = []
        if log_file.exists():
            try:
                entries = json.loads(log_file.read_text(encoding='utf-8'))
            except Exception:
                entries = []
        entries.append(entry)
        log_file.write_text(json.dumps(entries, indent=2), encoding='utf-8')

        # Move to Done
        done_file = done_dir / approval_file.name
        approval_file.replace(done_file)
        print(f'Moved {approval_file.name} → /Done/')

    return True


def main():
    parser = argparse.ArgumentParser(
        description='AI Employee — WhatsApp Watcher (Silver Tier)'
    )
    parser.add_argument('--vault', required=True,
                        help='Absolute path to AI_Employee_Vault folder')
    parser.add_argument('--session', default=str(DEFAULT_SESSION_PATH),
                        help='Path to store WhatsApp session data')
    parser.add_argument('--no-headless', action='store_true',
                        help='Show browser window (required for first QR scan)')
    parser.add_argument('--setup-whatsapp', action='store_true',
                        help='Open browser to scan QR code and save WhatsApp session')
    parser.add_argument('--reply-approved', action='store_true',
                        help='Send approved APPROVAL_WHATSAPP_*.md replies from /Approved/ via browser UI')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulate without opening WhatsApp Web')
    args = parser.parse_args()

    if args.dry_run:
        os.environ['DRY_RUN'] = 'true'
        global DRY_RUN
        DRY_RUN = True

    vault_path = Path(args.vault).resolve()
    if not vault_path.exists():
        print(f'ERROR: Vault not found: {vault_path}')
        sys.exit(1)

    if args.setup_whatsapp:
        setup_whatsapp_session()
        sys.exit(0)

    if args.reply_approved:
        send_approved_replies(vault_path, dry_run=DRY_RUN)
        sys.exit(0)

    watcher = WhatsAppWatcher(
        vault_path=str(vault_path),
        session_path=Path(args.session),
        headless=not args.no_headless
    )
    watcher.run()


if __name__ == '__main__':
    main()
