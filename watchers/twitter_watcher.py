#!/usr/bin/env python3
"""
Twitter/X Watcher -- Gold Tier
================================
Posts approved content to Twitter/X via Playwright browser UI.
Also generates engagement summaries.

Usage:
  python twitter_watcher.py --vault AI_Employee_Vault --setup-twitter
  python twitter_watcher.py --vault AI_Employee_Vault --post-approved
  python twitter_watcher.py --vault AI_Employee_Vault --dry-run

Approval file format (AI_Employee_Vault/Approved/TWITTER_POST_*.md):
  ## Tweet Content
  <tweet text max 280 chars>

  ## Hashtags
  #tag1 #tag2
"""

import argparse
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TwitterWatcher] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

TWITTER_PROFILE_DIR = Path("config/twitter_profile")
DEFAULT_VAULT = Path("AI_Employee_Vault")
MAX_TWEET_LENGTH = 280


# ── Session Setup ─────────────────────────────────────────────────────────────

def setup_twitter_session(profile_dir=TWITTER_PROFILE_DIR):
    """Open browser for manual Twitter/X login -- saves persistent profile."""
    from playwright.sync_api import sync_playwright

    profile_dir = Path(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)
    print("1. Log in to your Twitter/X account")
    print("2. Once on home timeline, session will be saved automatically\n")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            slow_mo=500,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            ignore_default_args=["--enable-automation"],
            viewport={"width": 1280, "height": 800},
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        print("\nOpening X.com — bot detection disabled...")
        page.goto("https://x.com/login")
        try:
            # Wait for home timeline = successful login
            page.wait_for_selector("[data-testid='primaryColumn']", timeout=120000)
            print("Twitter/X session saved! Profile stored at:", profile_dir)
        except Exception:
            print("Timeout -- please try again.")
        finally:
            browser.close()


# ── Post Tweet ────────────────────────────────────────────────────────────────

def post_tweet(text, profile_dir=TWITTER_PROFILE_DIR, dry_run=False):
    """Post a tweet to Twitter/X via browser UI."""
    if dry_run:
        preview = text[:MAX_TWEET_LENGTH]
        print(f"\n[DRY RUN] Would tweet ({len(preview)} chars):\n{preview}")
        return {"status": "dry_run", "platform": "twitter", "chars": len(preview)}

    # Truncate if over limit
    if len(text) > MAX_TWEET_LENGTH:
        text = text[:MAX_TWEET_LENGTH - 3] + "..."
        logger.warning(f"Tweet truncated to {MAX_TWEET_LENGTH} chars")

    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
                slow_mo=200,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
                ignore_default_args=["--enable-automation"],
                viewport={"width": 1280, "height": 800},
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            page.goto("https://x.com/home", wait_until="domcontentloaded")
            time.sleep(4)

            # Press 'n' — Twitter keyboard shortcut to open compose dialog
            page.keyboard.press("n")
            time.sleep(2)

            # Wait for compose textarea to appear
            textarea = page.locator("[data-testid='tweetTextarea_0']").last
            textarea.wait_for(state="visible", timeout=15000)
            textarea.focus()
            time.sleep(0.5)

            # Use execCommand('insertText') to insert text into DraftJS editor.
            # keyboard.type() does NOT trigger DraftJS onChange; execCommand does.
            result = page.evaluate(
                """(text) => {
                    const el = document.querySelector('[data-testid="tweetTextarea_0"]');
                    el.focus();
                    return document.execCommand('insertText', false, text);
                }""",
                text,
            )
            logger.info(f"execCommand result: {result}")
            time.sleep(2)

            # The modal Post button has data-testid='tweetButton' (not tweetButtonInline)
            btn_state = page.evaluate(
                """() => {
                    const b = document.querySelector('[data-testid="tweetButton"]');
                    return b ? {disabled: b.disabled, found: true} : {found: false};
                }"""
            )
            logger.info(f"Post button state: {btn_state}")

            if not btn_state.get("found"):
                raise RuntimeError("Post button not found on page")
            if btn_state.get("disabled"):
                raise RuntimeError("Post button disabled — text not registered by editor")

            # JS native .click() bypasses the div#layers overlay that blocks Playwright clicks
            page.evaluate("document.querySelector('[data-testid=\"tweetButton\"]').click()")
            time.sleep(5)

            logger.info(f"Tweeted: {text[:60]}...")
            browser.close()
            return {"status": "success", "platform": "twitter", "preview": text[:80], "chars": len(text)}
    except Exception as e:
        logger.error(f"Tweet error: {e}")
        return {"status": "error", "platform": "twitter", "error": str(e)}


# ── Process Approved Posts ────────────────────────────────────────────────────

def send_approved_tweets(vault_path, dry_run=False, profile_dir=TWITTER_PROFILE_DIR):
    """Read TWITTER_POST_*.md from /Approved/, tweet, move to /Done/."""
    vault_path = Path(vault_path)
    approved_dir = vault_path / "Approved"
    done_dir = vault_path / "Done"
    logs_dir = vault_path / "Logs"
    logs_dir.mkdir(exist_ok=True)
    done_dir.mkdir(exist_ok=True)

    approved_files = list(approved_dir.glob("TWITTER_POST_*.md")) + \
                     list(approved_dir.glob("TWEET_*.md"))

    if not approved_files:
        print("No approved tweets found in /Approved/")
        return []

    results = []
    for af in approved_files:
        content = af.read_text(encoding="utf-8")

        # Parse tweet content
        content_match = re.search(r"## Tweet Content\s*\n+(.*?)(?:\n## |\Z)", content, re.DOTALL)
        tweet_text = content_match.group(1).strip() if content_match else ""

        # Parse hashtags
        hashtag_match = re.search(r"## Hashtags\s*\n+(.*?)(?:\n## |\Z)", content, re.DOTALL)
        hashtags = hashtag_match.group(1).strip() if hashtag_match else ""

        full_tweet = f"{tweet_text} {hashtags}".strip() if hashtags else tweet_text

        print(f"\nTweeting ({len(full_tweet)} chars): {full_tweet[:80]}...")

        result = post_tweet(full_tweet, profile_dir, dry_run)
        results.append(result)

        if not dry_run:
            af.rename(done_dir / af.name)
            print(f"Moved {af.name} -> /Done/")

        # Log
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": "twitter_post",
            "actor": "twitter_watcher",
            "target": "twitter_x",
            "parameters": {"preview": full_tweet[:80], "chars": len(full_tweet), "result": str(result)},
            "approval_status": "approved",
            "approved_by": "human",
            "result": result.get("status", "unknown"),
            "dry_run": dry_run,
        }
        log_file = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"
        entries = json.loads(log_file.read_text(encoding="utf-8")) if log_file.exists() else []
        entries.append(log_entry)
        log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    return results


# ── Draft Tweet from LinkedIn Post ───────────────────────────────────────────

def adapt_linkedin_to_tweet(linkedin_text):
    """Shorten a LinkedIn post to tweet length (280 chars) + add hashtags."""
    # Remove emojis and shorten
    lines = linkedin_text.strip().split("\n")
    first_line = lines[0] if lines else linkedin_text

    # Try to fit in 240 chars + space for hashtags
    if len(first_line) > 240:
        first_line = first_line[:237] + "..."

    return first_line


def create_tweet_draft(vault_path, source_linkedin_file=None):
    """Create a TWITTER_POST_*.md draft from a LinkedIn post draft."""
    vault_path = Path(vault_path)
    needs_action_dir = vault_path / "Needs_Action"
    needs_action_dir.mkdir(exist_ok=True)

    tweet_content = "Check out our latest products and services! AI automation for small businesses."
    hashtags = "#AI #Automation #SmallBusiness #Productivity"

    if source_linkedin_file:
        li_path = vault_path / "Needs_Action" / source_linkedin_file
        if li_path.exists():
            li_text = li_path.read_text(encoding="utf-8")
            content_match = re.search(r"### Option A.*?```\n(.*?)\n```", li_text, re.DOTALL)
            if content_match:
                tweet_content = adapt_linkedin_to_tweet(content_match.group(1))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    draft_file = needs_action_dir / f"TWITTER_POST_DRAFT_{timestamp}.md"
    draft_file.write_text(
        f"---\ntype: twitter_post_draft\ncreated: {datetime.now().isoformat()}\n"
        f"status: pending_approval\nrequires_approval: true\n---\n\n"
        f"## Twitter/X Post Draft\n\n"
        f"## Tweet Content\n{tweet_content}\n\n"
        f"## Hashtags\n{hashtags}\n\n"
        f"**Character count:** {len(tweet_content) + len(hashtags) + 1}/{MAX_TWEET_LENGTH}\n\n"
        f"## To Approve\nMove to /Approved/ then run:\n"
        f"```\npython -X utf8 watchers/twitter_watcher.py --vault AI_Employee_Vault --post-approved\n```\n",
        encoding="utf-8",
    )
    print(f"Tweet draft created: {draft_file.name}")
    return draft_file


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Twitter/X Watcher (Gold Tier)")
    parser.add_argument("--vault", required=True)
    parser.add_argument("--setup-twitter", action="store_true", help="Open browser for Twitter/X login")
    parser.add_argument("--post-approved", action="store_true", help="Post approved tweets from /Approved/")
    parser.add_argument("--create-draft", action="store_true", help="Create a tweet draft in /Needs_Action/")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--profile", default=str(TWITTER_PROFILE_DIR))
    args = parser.parse_args()

    vault = Path(args.vault)
    profile = Path(args.profile)

    if args.setup_twitter:
        setup_twitter_session(profile)
    elif args.post_approved:
        send_approved_tweets(vault, args.dry_run, profile)
    elif args.create_draft:
        create_tweet_draft(vault)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
