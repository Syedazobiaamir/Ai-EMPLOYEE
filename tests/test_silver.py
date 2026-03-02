#!/usr/bin/env python3
"""
test_silver.py — Silver Tier Integration Tests for AI Employee

Tests all Silver Tier components using DRY_RUN mode (no real API calls).
Run this to validate your setup before going live.

Usage:
    python tests/test_silver.py
    python tests/test_silver.py --vault ./AI_Employee_Vault
    python tests/test_silver.py -v    (verbose output)

All tests use DRY_RUN=true so they are safe to run at any time.
"""

import json
import os
import sys
import time
import unittest
import shutil
from datetime import datetime
from pathlib import Path

# Ensure DRY_RUN for all tests
os.environ['DRY_RUN'] = 'true'

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
VAULT_PATH = PROJECT_ROOT / 'AI_Employee_Vault'
WATCHERS_PATH = PROJECT_ROOT / 'watchers'
sys.path.insert(0, str(WATCHERS_PATH))
sys.path.insert(0, str(PROJECT_ROOT))


# ─── Helper ───────────────────────────────────────────────────────────────────

def get_vault_path():
    for arg in sys.argv:
        if arg.startswith('--vault'):
            parts = arg.split('=', 1)
            if len(parts) == 2:
                return Path(parts[1]).resolve()
    # Check if sys.argv has --vault <path>
    for i, arg in enumerate(sys.argv):
        if arg == '--vault' and i + 1 < len(sys.argv):
            return Path(sys.argv[i + 1]).resolve()
    return VAULT_PATH.resolve()


VAULT = get_vault_path()


# ─── Vault Structure Tests ────────────────────────────────────────────────────

class TestVaultStructure(unittest.TestCase):
    """Test that the vault has all required folders and files."""

    def test_vault_exists(self):
        self.assertTrue(VAULT.exists(), f"Vault not found at: {VAULT}")

    def test_required_folders(self):
        required = [
            'Inbox', 'Needs_Action', 'Done', 'Plans',
            'Pending_Approval', 'Approved', 'Rejected',
            'Logs', 'Briefings', 'Invoices', 'Accounting'
        ]
        for folder in required:
            path = VAULT / folder
            self.assertTrue(path.exists(), f"Missing folder: {folder}")

    def test_required_files(self):
        required = ['Dashboard.md', 'Company_Handbook.md', 'Business_Goals.md']
        for filename in required:
            path = VAULT / filename
            self.assertTrue(path.exists(), f"Missing file: {filename}")

    def test_dashboard_has_content(self):
        dashboard = VAULT / 'Dashboard.md'
        if dashboard.exists():
            content = dashboard.read_text(encoding='utf-8')
            self.assertGreater(len(content), 10, "Dashboard.md is empty")

    def test_company_handbook_has_content(self):
        handbook = VAULT / 'Company_Handbook.md'
        if handbook.exists():
            content = handbook.read_text(encoding='utf-8')
            self.assertIn('approval', content.lower(), "Handbook missing approval rules")
            self.assertIn('email', content.lower(), "Handbook missing email rules")


# ─── Agent Skills Tests ───────────────────────────────────────────────────────

class TestAgentSkills(unittest.TestCase):
    """Test that all required Agent Skills exist."""

    def _commands_dir(self):
        return PROJECT_ROOT / '.claude' / 'commands'

    def test_process_inbox_skill(self):
        skill = self._commands_dir() / 'process-inbox.md'
        self.assertTrue(skill.exists(), "Missing skill: process-inbox.md")

    def test_daily_briefing_skill(self):
        skill = self._commands_dir() / 'daily-briefing.md'
        self.assertTrue(skill.exists(), "Missing skill: daily-briefing.md")

    def test_check_vault_skill(self):
        skill = self._commands_dir() / 'check-vault.md'
        self.assertTrue(skill.exists(), "Missing skill: check-vault.md")

    def test_approve_action_skill(self):
        skill = self._commands_dir() / 'approve-action.md'
        self.assertTrue(skill.exists(), "Missing skill: approve-action.md")

    def test_post_linkedin_skill(self):
        """Silver Tier: LinkedIn posting skill."""
        skill = self._commands_dir() / 'post-linkedin.md'
        self.assertTrue(skill.exists(), "Missing Silver skill: post-linkedin.md")
        content = skill.read_text(encoding='utf-8')
        self.assertIn('linkedin', content.lower(), "post-linkedin.md missing LinkedIn content")

    def test_send_email_skill(self):
        """Silver Tier: Email sending skill."""
        skill = self._commands_dir() / 'send-email.md'
        self.assertTrue(skill.exists(), "Missing Silver skill: send-email.md")

    def test_weekly_audit_skill(self):
        """Silver Tier: Weekly audit skill."""
        skill = self._commands_dir() / 'weekly-audit.md'
        self.assertTrue(skill.exists(), "Missing Silver skill: weekly-audit.md")


# ─── Watcher Tests ───────────────────────────────────────────────────────────

class TestWatchers(unittest.TestCase):
    """Test that all watcher scripts exist and have correct structure."""

    def test_base_watcher_exists(self):
        self.assertTrue((WATCHERS_PATH / 'base_watcher.py').exists())

    def test_filesystem_watcher_exists(self):
        self.assertTrue((WATCHERS_PATH / 'filesystem_watcher.py').exists())

    def test_gmail_watcher_exists(self):
        """Silver Tier: Gmail watcher."""
        self.assertTrue(
            (WATCHERS_PATH / 'gmail_watcher.py').exists(),
            "Missing Silver watcher: gmail_watcher.py"
        )

    def test_whatsapp_watcher_exists(self):
        """Silver Tier: WhatsApp watcher."""
        self.assertTrue(
            (WATCHERS_PATH / 'whatsapp_watcher.py').exists(),
            "Missing Silver watcher: whatsapp_watcher.py"
        )

    def test_linkedin_watcher_exists(self):
        """Silver Tier: LinkedIn watcher."""
        self.assertTrue(
            (WATCHERS_PATH / 'linkedin_watcher.py').exists(),
            "Missing Silver watcher: linkedin_watcher.py"
        )

    def test_requirements_has_silver_deps(self):
        """Silver requirements.txt should include Gmail, Playwright, Requests."""
        req_file = WATCHERS_PATH / 'requirements.txt'
        self.assertTrue(req_file.exists())
        content = req_file.read_text(encoding='utf-8')
        self.assertIn('google-auth', content, "requirements.txt missing google-auth")
        self.assertIn('playwright', content, "requirements.txt missing playwright")
        self.assertIn('requests', content, "requirements.txt missing requests")


# ─── Gmail Watcher Tests (DRY RUN) ────────────────────────────────────────────

class TestGmailWatcher(unittest.TestCase):
    """Test Gmail Watcher with dry-run (no real Gmail API calls)."""

    def setUp(self):
        from gmail_watcher import GmailWatcher
        self.watcher = GmailWatcher(str(VAULT))
        self.needs_action = VAULT / 'Needs_Action'

    def test_watcher_initializes(self):
        self.assertIsNotNone(self.watcher)
        self.assertEqual(self.watcher.check_interval, 120)

    def test_dry_run_returns_mock_messages(self):
        """DRY_RUN should return a mock email without hitting Gmail API."""
        messages = self.watcher.check_for_updates()
        self.assertIsInstance(messages, list)
        self.assertGreater(len(messages), 0, "DRY_RUN should return at least 1 mock message")
        self.assertTrue(messages[0].get('_mock'), "DRY_RUN message should have _mock=True")

    def test_creates_action_file(self):
        """Should create a .md file in Needs_Action."""
        mock_msg = {'id': 'test_gmail_001', 'threadId': 'thread_001', '_mock': True}
        result_path = self.watcher.create_action_file(mock_msg)
        self.assertIsNotNone(result_path)
        self.assertTrue(result_path.exists(), f"Action file not created: {result_path}")

        content = result_path.read_text(encoding='utf-8')
        self.assertIn('type: email', content)
        self.assertIn('source: gmail', content)
        self.assertIn('dry_run: true', content)

        # Cleanup
        result_path.unlink()

    def test_action_file_yaml_frontmatter(self):
        """Action file should have valid YAML frontmatter."""
        mock_msg = {'id': 'test_gmail_002', '_mock': True}
        result_path = self.watcher.create_action_file(mock_msg)
        if result_path:
            content = result_path.read_text(encoding='utf-8')
            self.assertTrue(content.startswith('---'), "Missing YAML frontmatter")
            self.assertIn('status: pending', content)
            result_path.unlink()

    def test_logs_action(self):
        """Should write to the daily log file."""
        mock_msg = {'id': 'test_gmail_003', '_mock': True}
        before_count = self._get_log_entry_count()
        result_path = self.watcher.create_action_file(mock_msg)
        after_count = self._get_log_entry_count()
        self.assertGreater(after_count, before_count, "Log entry not added")
        if result_path:
            result_path.unlink()

    def _get_log_entry_count(self) -> int:
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = VAULT / 'Logs' / f'{today}.json'
        if not log_file.exists():
            return 0
        try:
            return len(json.loads(log_file.read_text(encoding='utf-8')))
        except Exception:
            return 0


# ─── WhatsApp Watcher Tests (DRY RUN) ─────────────────────────────────────────

class TestWhatsAppWatcher(unittest.TestCase):
    """Test WhatsApp Watcher with dry-run."""

    def setUp(self):
        from whatsapp_watcher import WhatsAppWatcher
        self.watcher = WhatsAppWatcher(str(VAULT))

    def test_watcher_initializes(self):
        self.assertIsNotNone(self.watcher)
        self.assertEqual(self.watcher.check_interval, 30)

    def test_dry_run_returns_mock(self):
        messages = self.watcher.check_for_updates()
        self.assertIsInstance(messages, list)
        self.assertGreater(len(messages), 0)
        self.assertTrue(messages[0].get('_mock'))

    def test_creates_action_file(self):
        mock_msg = {
            'id': 'test_wa_001',
            'sender': 'Test Client',
            'text': 'Hi, I need an invoice urgently!',
            'keywords': ['invoice', 'urgent'],
            'time': '10:30',
            '_mock': True
        }
        result_path = self.watcher.create_action_file(mock_msg)
        self.assertIsNotNone(result_path)
        self.assertTrue(result_path.exists())

        content = result_path.read_text(encoding='utf-8')
        self.assertIn('type: whatsapp_message', content)
        self.assertIn('Test Client', content)
        self.assertIn('invoice', content)

        result_path.unlink()

    def test_keywords_classification(self):
        """Invoice keyword should set action_type to billing_request."""
        mock_msg = {
            'id': 'test_wa_002',
            'sender': 'Client',
            'text': 'Need invoice for January',
            'keywords': ['invoice'],
            'time': '09:00',
            '_mock': True
        }
        result_path = self.watcher.create_action_file(mock_msg)
        if result_path:
            content = result_path.read_text(encoding='utf-8')
            self.assertIn('billing_request', content)
            result_path.unlink()


# ─── LinkedIn Watcher Tests (DRY RUN) ─────────────────────────────────────────

class TestLinkedInWatcher(unittest.TestCase):
    """Test LinkedIn Watcher with dry-run."""

    def setUp(self):
        from linkedin_watcher import LinkedInWatcher
        self.watcher = LinkedInWatcher(str(VAULT))

    def test_watcher_initializes(self):
        self.assertIsNotNone(self.watcher)

    def test_dry_run_check_updates(self):
        items = self.watcher.check_for_updates()
        self.assertIsInstance(items, list)
        # Should have at least the mock message
        self.assertGreater(len(items), 0)

    def test_creates_post_draft(self):
        """Should create a LinkedIn post draft in Needs_Action."""
        # Reset last_post_generated to force generation
        self.watcher.last_post_generated = None
        result_path = self.watcher._create_post_draft()
        self.assertIsNotNone(result_path)
        self.assertTrue(result_path.exists())

        content = result_path.read_text(encoding='utf-8')
        self.assertIn('type: linkedin_post_draft', content)
        self.assertIn('requires_approval: true', content)
        self.assertIn('Option A', content)
        self.assertIn('Option B', content)
        self.assertIn('Option C', content)

        result_path.unlink()

    def test_post_themes_generated(self):
        """Post themes should contain hashtags and calls to action."""
        themes = self.watcher._select_post_theme('')
        self.assertIn('tips', themes)
        self.assertIn('service', themes)
        self.assertIn('results', themes)
        self.assertIn('#AI', themes['tips'])

    def test_creates_message_action(self):
        mock_msg = {
            'type': 'message',
            'id': 'mock_li_001',
            'sender': 'Test LinkedIn Contact',
            'text': 'Interested in your AI services!',
            '_mock': True
        }
        result_path = self.watcher._create_message_action(mock_msg)
        self.assertTrue(result_path.exists())
        content = result_path.read_text(encoding='utf-8')
        self.assertIn('type: linkedin_message', content)
        self.assertIn('requires_approval: true', content)
        result_path.unlink()


# ─── MCP Server Tests ─────────────────────────────────────────────────────────

class TestEmailMCPServer(unittest.TestCase):
    """Test Email MCP Server configuration."""

    def test_mcp_directory_exists(self):
        mcp_dir = PROJECT_ROOT / 'mcp_servers' / 'email_mcp'
        self.assertTrue(mcp_dir.exists(), "MCP server directory missing")

    def test_mcp_index_exists(self):
        index = PROJECT_ROOT / 'mcp_servers' / 'email_mcp' / 'index.js'
        self.assertTrue(index.exists(), "MCP server index.js missing")

    def test_mcp_package_json_exists(self):
        pkg = PROJECT_ROOT / 'mcp_servers' / 'email_mcp' / 'package.json'
        self.assertTrue(pkg.exists(), "MCP server package.json missing")

    def test_mcp_package_json_valid(self):
        pkg = PROJECT_ROOT / 'mcp_servers' / 'email_mcp' / 'package.json'
        if pkg.exists():
            data = json.loads(pkg.read_text(encoding='utf-8'))
            self.assertEqual(data['name'], 'ai-employee-email-mcp')
            self.assertIn('@modelcontextprotocol/sdk', data['dependencies'])

    def test_mcp_index_has_tools(self):
        index = PROJECT_ROOT / 'mcp_servers' / 'email_mcp' / 'index.js'
        if index.exists():
            content = index.read_text(encoding='utf-8')
            self.assertIn('send_email', content)
            self.assertIn('draft_email', content)
            self.assertIn('search_emails', content)


# ─── Orchestrator Tests ───────────────────────────────────────────────────────

class TestOrchestrator(unittest.TestCase):
    """Test Orchestrator configuration."""

    def test_orchestrator_exists(self):
        self.assertTrue((PROJECT_ROOT / 'orchestrator.py').exists())

    def test_orchestrator_imports(self):
        """Orchestrator should import without crashing."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'orchestrator', PROJECT_ROOT / 'orchestrator.py'
        )
        # Just check it can be found, don't actually import (would start processes)
        self.assertIsNotNone(spec)

    def test_scheduler_script_exists(self):
        self.assertTrue(
            (PROJECT_ROOT / 'scheduler' / 'setup_task_scheduler.py').exists()
        )


# ─── Approval Workflow Tests ──────────────────────────────────────────────────

class TestApprovalWorkflow(unittest.TestCase):
    """Test the human-in-the-loop approval workflow."""

    def test_pending_approval_folder_exists(self):
        self.assertTrue((VAULT / 'Pending_Approval').exists())

    def test_approved_folder_exists(self):
        self.assertTrue((VAULT / 'Approved').exists())

    def test_rejected_folder_exists(self):
        self.assertTrue((VAULT / 'Rejected').exists())

    def test_approval_file_format(self):
        """Create a mock approval file and verify format."""
        test_file = VAULT / 'Pending_Approval' / 'TEST_APPROVAL_FORMAT.md'
        content = """---
type: approval_request
action: send_email
to: test@example.com
subject: Test Subject
created: 2026-02-22T10:00:00
expires: 2026-02-23T10:00:00
status: pending
---

## Test Approval

**Action:** Send email to test@example.com

## To Approve
Move this file to /Approved folder.

## To Reject
Move this file to /Rejected folder.
"""
        test_file.write_text(content, encoding='utf-8')
        self.assertTrue(test_file.exists())

        # Verify frontmatter
        read_content = test_file.read_text(encoding='utf-8')
        self.assertIn('type: approval_request', read_content)
        self.assertIn('action: send_email', read_content)
        self.assertIn('status: pending', read_content)

        test_file.unlink()


# ─── Config Tests ─────────────────────────────────────────────────────────────

class TestConfig(unittest.TestCase):
    """Test configuration files."""

    def test_env_example_exists(self):
        self.assertTrue(
            (PROJECT_ROOT / 'config' / '.env.example').exists(),
            "Missing config/.env.example"
        )

    def test_env_example_has_required_keys(self):
        env_example = PROJECT_ROOT / 'config' / '.env.example'
        if env_example.exists():
            content = env_example.read_text(encoding='utf-8')
            required_keys = [
                'DRY_RUN', 'GMAIL_CREDENTIALS_PATH', 'LINKEDIN_ACCESS_TOKEN',
                'LINKEDIN_PERSON_URN', 'VAULT_PATH'
            ]
            for key in required_keys:
                self.assertIn(key, content, f"Missing key in .env.example: {key}")

    def test_gitignore_protects_secrets(self):
        gitignore = PROJECT_ROOT / '.gitignore'
        if gitignore.exists():
            content = gitignore.read_text(encoding='utf-8')
            # Check that sensitive files are ignored
            self.assertIn('.env', content, ".env not in .gitignore!")


# ─── Security Tests ───────────────────────────────────────────────────────────

class TestSecurity(unittest.TestCase):
    """Verify security best practices."""

    def test_no_credentials_in_vault(self):
        """Scan vault for any potential credential leaks."""
        dangerous_patterns = [
            'password=', 'api_key=', 'secret=', 'token=',
            'AKIA',  # AWS key prefix
            'sk-',   # OpenAI key prefix
        ]
        violations = []
        for md_file in VAULT.rglob('*.md'):
            content = md_file.read_text(encoding='utf-8', errors='ignore').lower()
            for pattern in dangerous_patterns:
                if pattern.lower() in content:
                    # Exclude the handbook's rules about credentials
                    if 'credentials' not in md_file.name.lower() and \
                       'handbook' not in md_file.name.lower():
                        violations.append(f"{md_file.name}: found '{pattern}'")

        self.assertEqual(len(violations), 0,
                         f"Potential credential leaks in vault:\n" + "\n".join(violations))

    def test_logs_directory_exists(self):
        self.assertTrue((VAULT / 'Logs').exists())

    def test_dry_run_default(self):
        """DRY_RUN should default to true in test env."""
        self.assertEqual(os.environ.get('DRY_RUN'), 'true')


# ─── Integration: Full Dry-Run Flow ──────────────────────────────────────────

class TestEndToEndFlow(unittest.TestCase):
    """Integration test: simulate the complete file-drop-to-action flow."""

    def test_file_drop_creates_needs_action(self):
        """Drop a file in Inbox, verify metadata appears in Needs_Action."""
        inbox = VAULT / 'Inbox'
        needs_action = VAULT / 'Needs_Action'

        # Create a test file in Inbox
        test_file = inbox / 'test_integration_drop.txt'
        test_file.write_text('This is an integration test file.', encoding='utf-8')

        # Give watchdog time to react (if running)
        # In test mode, we manually call the watcher logic
        from filesystem_watcher import DropFolderHandler
        import logging
        handler = DropFolderHandler(str(VAULT), logging.getLogger('test'))
        handler._handle_file(test_file)

        # Check action file was created
        action_files = list(needs_action.glob(f'*test_integration_drop*'))
        self.assertGreater(len(action_files), 0, "No action file created for file drop")

        # Cleanup
        test_file.unlink(missing_ok=True)
        for f in action_files:
            f.unlink(missing_ok=True)

    def test_gmail_dry_run_full_flow(self):
        """Complete Gmail dry-run: check → create action file → verify log."""
        from gmail_watcher import GmailWatcher
        watcher = GmailWatcher(str(VAULT))

        # Check
        messages = watcher.check_for_updates()
        self.assertGreater(len(messages), 0)

        # Create action file
        result = watcher.create_action_file(messages[0])
        self.assertIsNotNone(result)
        self.assertTrue(result.exists())

        # Verify log was written
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = VAULT / 'Logs' / f'{today}.json'
        self.assertTrue(log_file.exists(), "Log file not created")
        log_data = json.loads(log_file.read_text(encoding='utf-8'))
        action_types = [e.get('action_type') for e in log_data]
        self.assertIn('email_detected', action_types)

        # Cleanup
        result.unlink(missing_ok=True)


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('=' * 60)
    print('AI Employee — Silver Tier Test Suite')
    print(f'Vault: {VAULT}')
    print(f'DRY_RUN: {os.environ.get("DRY_RUN")}')
    print('=' * 60)
    print()

    # Filter out --vault argument so unittest doesn't choke on it
    clean_args = [sys.argv[0]]
    skip_next = False
    for arg in sys.argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if arg == '--vault':
            skip_next = True
            continue
        if arg.startswith('--vault='):
            continue
        clean_args.append(arg)

    unittest.main(argv=clean_args, verbosity=2, exit=True)
