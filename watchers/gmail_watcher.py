#!/usr/bin/env python3
"""
gmail_watcher.py — Gmail Watcher for AI Employee (Silver Tier)

Monitors Gmail for unread important emails every 2 minutes.
When a new important email is found, it creates an action .md file
in /Needs_Action for Claude to process.

Setup:
    1. Enable Gmail API in Google Cloud Console
    2. Download OAuth credentials as credentials.json
    3. Run once interactively to authorize: python gmail_watcher.py --vault ./AI_Employee_Vault --auth
    4. After auth, run normally: python gmail_watcher.py --vault ./AI_Employee_Vault

Usage:
    python gmail_watcher.py --vault /path/to/AI_Employee_Vault
    python gmail_watcher.py --vault /path/to/AI_Employee_Vault --dry-run
    python gmail_watcher.py --vault /path/to/AI_Employee_Vault --auth

Dependencies:
    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
"""

import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent dir to path so we can import base_watcher
sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher

DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
]

# Default credentials locations
DEFAULT_CREDENTIALS = Path(__file__).parent.parent / 'config' / 'gmail_credentials.json'
DEFAULT_TOKEN = Path(__file__).parent.parent / 'config' / 'gmail_token.json'
DEFAULT_GMAIL_SESSION = Path(__file__).parent.parent / 'config' / 'gmail_session.json'


def get_gmail_service(credentials_path: Path, token_path: Path):
    """Authenticate and return a Gmail API service client."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: Missing Google API libraries.")
        print("Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        sys.exit(1)

    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"Gmail credentials not found at: {credentials_path}\n"
                    "Download your OAuth credentials from Google Cloud Console\n"
                    "and save as: config/gmail_credentials.json"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())
        print(f"Token saved to: {token_path}")

    return build('gmail', 'v1', credentials=creds)


def extract_email_body(payload: dict) -> str:
    """Extract plain text body from Gmail message payload."""
    body = ''
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data + '==').decode('utf-8', errors='replace')
                    break
            elif 'parts' in part:
                # Recurse into nested parts
                body = extract_email_body(part)
                if body:
                    break
    else:
        data = payload.get('body', {}).get('data', '')
        if data:
            body = base64.urlsafe_b64decode(data + '==').decode('utf-8', errors='replace')

    return body.strip()


class GmailWatcher(BaseWatcher):
    """
    Silver Tier Watcher: Monitors Gmail for important unread emails.
    Polls every 2 minutes (120 seconds) to respect API quotas.
    """

    def __init__(self, vault_path: str, credentials_path: Path = DEFAULT_CREDENTIALS,
                 token_path: Path = DEFAULT_TOKEN):
        super().__init__(vault_path, check_interval=120)
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.processed_ids: set = set()
        self._load_processed_ids()

    def _load_processed_ids(self):
        """Load already-processed email IDs from a state file."""
        state_file = self.vault_path / 'Logs' / 'gmail_processed.json'
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding='utf-8'))
                self.processed_ids = set(data.get('processed_ids', []))
                self.logger.info(f'Loaded {len(self.processed_ids)} previously processed email IDs')
            except Exception as e:
                self.logger.warning(f'Could not load processed IDs: {e}')

    def _save_processed_ids(self):
        """Persist processed email IDs."""
        state_file = self.vault_path / 'Logs' / 'gmail_processed.json'
        try:
            state_file.write_text(
                json.dumps({'processed_ids': list(self.processed_ids)}, indent=2),
                encoding='utf-8'
            )
        except Exception as e:
            self.logger.warning(f'Could not save processed IDs: {e}')

    def _connect(self):
        """Lazy-connect to Gmail API."""
        if self.service is None:
            self.logger.info('Connecting to Gmail API...')
            self.service = get_gmail_service(self.credentials_path, self.token_path)
            self.logger.info('Gmail API connected.')

    def check_for_updates(self) -> list:
        """Poll Gmail for unread important messages."""
        if DRY_RUN:
            self.logger.info('[DRY RUN] Simulating Gmail check — returning mock email')
            return [{'id': 'mock_001', 'threadId': 'thread_001', '_mock': True}]

        self._connect()
        try:
            # Query: unread messages marked important OR labeled IMPORTANT
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread (is:important OR label:IMPORTANT)',
                maxResults=10
            ).execute()
            messages = results.get('messages', [])
            # Filter out already processed
            new_messages = [m for m in messages if m['id'] not in self.processed_ids]
            if new_messages:
                self.logger.info(f'Found {len(new_messages)} new important email(s)')
            return new_messages
        except Exception as e:
            self.logger.error(f'Gmail API error: {e}')
            return []

    def create_action_file(self, message: dict) -> Path:
        """Create a Needs_Action .md file for a Gmail message."""
        msg_id = message['id']

        if message.get('_mock'):
            # Dry-run / mock message
            from_addr = 'mock.client@example.com'
            subject = 'Mock: Invoice Request (DRY RUN)'
            snippet = 'This is a simulated email for dry-run testing purposes.'
            body = snippet
            received = datetime.now().isoformat()
        else:
            try:
                msg = self.service.users().messages().get(
                    userId='me', id=msg_id, format='full'
                ).execute()
                headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
                from_addr = headers.get('From', 'Unknown')
                subject = headers.get('Subject', '(No Subject)')
                received = headers.get('Date', datetime.now().isoformat())
                snippet = msg.get('snippet', '')
                body = extract_email_body(msg['payload']) or snippet
            except Exception as e:
                self.logger.error(f'Failed to fetch email {msg_id}: {e}')
                return None

        # Determine priority based on keywords
        priority = 'high' if any(kw in (subject + body).lower()
                                  for kw in ['urgent', 'asap', 'invoice', 'payment', 'overdue', 'contract']) \
            else 'normal'

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'EMAIL_{timestamp}_{msg_id[:8]}.md'
        filepath = self.needs_action / filename

        content = f"""---
type: email
source: gmail
message_id: {msg_id}
from: {from_addr}
subject: {subject}
received: {received}
priority: {priority}
status: pending
dry_run: {str(DRY_RUN).lower()}
---

## Email Summary
**From:** {from_addr}
**Subject:** {subject}
**Received:** {received}
**Priority:** {priority}

## Content Preview
{snippet}

## Full Body
{body[:2000]}{'...(truncated)' if len(body) > 2000 else ''}

## Suggested Actions
- [ ] Review sender — known contact or new?
- [ ] Draft reply if response needed
- [ ] Create invoice if requested
- [ ] Forward to relevant party if needed
- [ ] Archive after processing

## AI Employee Notes
_This email was flagged as important by Gmail. Process per Company_Handbook rules._
"""

        if DRY_RUN:
            self.logger.info(f'[DRY RUN] Would create: {filepath}')
            # Still write file in dry-run so Claude can test the workflow
            filepath.write_text(content, encoding='utf-8')
        else:
            filepath.write_text(content, encoding='utf-8')

        self.processed_ids.add(msg_id)
        self._save_processed_ids()
        self._log_action(msg_id, from_addr, subject, filename)

        return filepath

    def _log_action(self, msg_id: str, from_addr: str, subject: str, filename: str):
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs / f'{today}.json'
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": "email_detected",
            "actor": "gmail_watcher",
            "target": from_addr,
            "parameters": {"subject": subject, "message_id": msg_id},
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


def setup_gmail_session(session_path: Path = DEFAULT_GMAIL_SESSION):
    """Open a visible browser so the user can log in to Gmail and save the session."""
    from playwright.sync_api import sync_playwright

    session_path.parent.mkdir(parents=True, exist_ok=True)
    print('Opening Gmail in browser. Log in, then press Enter here to save session.')

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=300,
            args=['--no-sandbox', '--window-size=1280,900'],
        )
        ctx = browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/122.0.0.0 Safari/537.36'
            ),
        )
        page = ctx.new_page()
        page.goto('https://mail.google.com')
        input('\nBrowser open — log in to Gmail, then press Enter here...\n')
        ctx.storage_state(path=str(session_path))
        print(f'Session saved to: {session_path}')
        browser.close()


def send_via_browser(to: str, subject: str, body: str,
                     session_path: Path = DEFAULT_GMAIL_SESSION) -> dict:
    """Compose and send an email via Gmail in a visible Playwright browser."""
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    print(f'\nOpening Gmail browser → sending to: {to}')

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500,
            args=['--no-sandbox', '--window-size=1280,900', '--window-position=100,50'],
        )
        ctx_kwargs = {
            'viewport': {'width': 1280, 'height': 900},
            'user_agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/122.0.0.0 Safari/537.36'
            ),
        }
        if session_path.exists():
            ctx_kwargs['storage_state'] = str(session_path)
            print(f'Loaded Gmail session: {session_path}')
        else:
            print(f'WARNING: No Gmail session at {session_path}')
            print('Run: python gmail_watcher.py --vault AI_Employee_Vault --setup-gmail')

        ctx = browser.new_context(**ctx_kwargs)
        page = ctx.new_page()

        try:
            page.goto('https://mail.google.com')
            # Wait for inbox to load
            page.wait_for_selector('[gh="cm"], [data-tooltip="Compose"]', timeout=30000)
            print('Gmail loaded.')

            # Click Compose
            page.locator('[gh="cm"]').first.click()
            print('Compose clicked.')

            # Wait for compose window To field
            page.wait_for_selector('div[name="to"]', timeout=10000)

            # Fill To
            page.locator('div[name="to"]').click()
            page.keyboard.type(to)
            page.keyboard.press('Tab')
            print(f'To: {to}')

            # Fill Subject
            page.locator('input[name="subjectbox"]').click()
            page.keyboard.type(subject)
            print(f'Subject: {subject}')

            # Fill Body
            page.locator('div[aria-label="Message Body"]').click()
            page.keyboard.type(body)
            print(f'Body typed ({len(body)} chars)')

            # Send via Ctrl+Enter (most reliable Gmail shortcut)
            page.keyboard.press('Control+Enter')
            print('Email sent!')

            page.wait_for_timeout(3000)
            return {'status': 'sent', 'method': 'browser_ui', 'to': to, 'subject': subject}

        except PlaywrightTimeout as e:
            print(f'Timeout: {e}')
            return {'status': 'error', 'method': 'browser_ui', 'error': str(e)}
        except Exception as e:
            print(f'Error: {e}')
            return {'status': 'error', 'method': 'browser_ui', 'error': str(e)}
        finally:
            page.wait_for_timeout(2000)
            browser.close()


def send_approved_emails(vault_path: Path, dry_run: bool = False,
                         session_path: Path = DEFAULT_GMAIL_SESSION):
    """Send all approved APPROVAL_EMAIL_*.md files from /Approved/ via browser UI."""
    import re

    approved_dir = vault_path / 'Approved'
    done_dir = vault_path / 'Done'
    logs_dir = vault_path / 'Logs'

    found = list(approved_dir.glob('APPROVAL_EMAIL_*.md'))
    if not found:
        print('No approved email files found in /Approved/')
        return False

    for approval_file in found:
        content = approval_file.read_text(encoding='utf-8')

        # Parse **To:** line
        to_match = re.search(r'\*\*To:\*\*\s*(.+)', content)
        to_addr = to_match.group(1).strip() if to_match else None
        # Fallback to frontmatter target:
        if not to_addr:
            fm_match = re.search(r'^target:\s*(.+)$', content, re.MULTILINE)
            to_addr = fm_match.group(1).strip() if fm_match else None

        # Parse **Subject:**
        subj_match = re.search(r'\*\*Subject:\*\*\s*(.+)', content)
        subject = subj_match.group(1).strip() if subj_match else '(No Subject)'

        # Extract body between the --- dividers after "Draft Reply:"
        body_match = re.search(r'\*\*Draft Reply:\*\*\s*\n+---\n+(.*?)\n+---', content, re.DOTALL)
        body = body_match.group(1).strip() if body_match else ''

        if not to_addr or not body:
            print(f'Could not parse To/Body from {approval_file.name} — skipping')
            continue

        print(f'\nApproved email:')
        print(f'  To:      {to_addr}')
        print(f'  Subject: {subject}')
        print(f'  Preview: {body[:80]}...')

        if dry_run:
            print('[DRY RUN] Would send via Gmail browser. File stays in /Approved/')
            continue

        result = send_via_browser(to_addr, subject, body, session_path)
        print(f'Result: {result}')

        # Log
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = logs_dir / f'{today}.json'
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": "email_sent_browser",
            "actor": "gmail_watcher",
            "target": to_addr,
            "parameters": {"subject": subject, "method": "browser_ui"},
            "approval_status": "approved",
            "approved_by": "human",
            "result": result.get('status', 'unknown'),
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
        description='AI Employee — Gmail Watcher (Silver Tier)'
    )
    parser.add_argument('--vault', required=True,
                        help='Absolute path to AI_Employee_Vault folder')
    parser.add_argument('--credentials', default=str(DEFAULT_CREDENTIALS),
                        help='Path to Gmail OAuth credentials JSON')
    parser.add_argument('--token', default=str(DEFAULT_TOKEN),
                        help='Path to store OAuth token JSON')
    parser.add_argument('--auth', action='store_true',
                        help='Run OAuth authentication flow and exit')
    parser.add_argument('--setup-gmail', action='store_true',
                        help='Open browser to log in to Gmail and save session for browser sending')
    parser.add_argument('--send-approved', action='store_true',
                        help='Send approved APPROVAL_EMAIL_*.md files from /Approved/ via browser UI')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulate without hitting the Gmail API')
    args = parser.parse_args()

    if args.dry_run:
        os.environ['DRY_RUN'] = 'true'
        global DRY_RUN
        DRY_RUN = True

    vault_path = Path(args.vault).resolve()
    if not vault_path.exists():
        print(f'ERROR: Vault not found: {vault_path}')
        sys.exit(1)

    if args.auth:
        print('Running OAuth authentication flow...')
        get_gmail_service(Path(args.credentials), Path(args.token))
        print('Authentication complete. Token saved.')
        sys.exit(0)

    if args.setup_gmail:
        setup_gmail_session()
        sys.exit(0)

    if args.send_approved:
        send_approved_emails(vault_path, dry_run=DRY_RUN)
        sys.exit(0)

    watcher = GmailWatcher(
        vault_path=str(vault_path),
        credentials_path=Path(args.credentials),
        token_path=Path(args.token)
    )

    print(f"Gmail Watcher started. Polling every {watcher.check_interval}s")
    print(f"Dry-run mode: {DRY_RUN}")
    print("Press Ctrl+C to stop.\n")
    watcher.run()


if __name__ == '__main__':
    main()
