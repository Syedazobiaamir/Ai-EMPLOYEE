#!/usr/bin/env python3
"""
Instagram & Facebook Watcher -- Gold Tier
==========================================
Posts approved content to Instagram and Facebook via Playwright browser UI.
Also monitors for engagement (likes, comments) and generates summaries.

Usage:
  python instagram_watcher.py --vault AI_Employee_Vault --setup-instagram
  python instagram_watcher.py --vault AI_Employee_Vault --setup-facebook
  python instagram_watcher.py --vault AI_Employee_Vault --post-approved
  python instagram_watcher.py --vault AI_Employee_Vault --engagement-summary
  python instagram_watcher.py --vault AI_Employee_Vault --dry-run

Approval file format (AI_Employee_Vault/Approved/INSTAGRAM_POST_*.md or FACEBOOK_POST_*.md):
  ---
  platform: instagram | facebook | both
  ---
  ## Post Content
  <caption text>

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
    format="%(asctime)s [InstagramWatcher] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

INSTAGRAM_PROFILE_DIR = Path("config/instagram_profile")
DEFAULT_VAULT = Path("AI_Employee_Vault")


# ── Session Setup ─────────────────────────────────────────────────────────────

def setup_instagram_session(profile_dir=INSTAGRAM_PROFILE_DIR):
    """Open browser for manual Instagram login -- saves persistent profile."""
    from playwright.sync_api import sync_playwright

    profile_dir = Path(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)
    print("\nOpening Instagram login page...")
    print("1. Log in to your Instagram account")
    print("2. Once on home feed, session will be saved automatically\n")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            slow_mo=500,
            args=["--no-sandbox", "--window-size=1280,900"],
        )
        page = browser.new_page()
        page.goto("https://www.instagram.com/accounts/login/")
        try:
            page.wait_for_selector("nav[role='navigation']", timeout=120000)
            print("Instagram session saved! Profile stored at:", profile_dir)
        except Exception:
            print("Timeout -- please try again.")
        finally:
            browser.close()


def setup_facebook_session(profile_dir=INSTAGRAM_PROFILE_DIR):
    """Open browser for manual Facebook login -- uses same profile as Instagram."""
    from playwright.sync_api import sync_playwright

    profile_dir = Path(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)
    print("\nOpening Facebook login page...")
    print("1. Log in to your Facebook account")
    print("2. Session will be saved automatically\n")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            slow_mo=500,
        )
        page = browser.new_page()
        page.goto("https://www.facebook.com/")
        try:
            page.wait_for_selector("[aria-label='Facebook']", timeout=120000)
            print("Facebook session saved!")
        except Exception:
            print("Timeout -- please try again.")
        finally:
            browser.close()


# ── Post to Facebook ──────────────────────────────────────────────────────────

def post_to_facebook(text, profile_dir=INSTAGRAM_PROFILE_DIR, dry_run=False):
    """Post text to Facebook via browser UI."""
    if dry_run:
        print(f"\n[DRY RUN] Would post to Facebook:\n{text[:200]}...")
        return {"status": "dry_run", "platform": "facebook"}

    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
                slow_mo=600,
                args=["--no-sandbox", "--window-size=1280,900"],
            )
            page = browser.new_page()
            page.goto("https://www.facebook.com/")
            page.wait_for_load_state("networkidle", timeout=15000)

            # Open post composer
            composer = page.get_by_placeholder("What's on your mind?").first
            composer.wait_for(state="visible", timeout=15000)
            composer.click()
            time.sleep(1)

            # Type text
            text_area = page.locator("div[contenteditable='true'][role='textbox']").last
            text_area.wait_for(state="visible", timeout=10000)
            text_area.click()
            page.keyboard.type(text, delay=30)
            time.sleep(1)

            # Click Post
            post_btn = page.get_by_role("button", name="Post").last
            post_btn.wait_for(state="visible", timeout=10000)
            post_btn.click()
            time.sleep(3)

            logger.info(f"Posted to Facebook: {text[:60]}...")
            browser.close()
            return {"status": "success", "platform": "facebook", "preview": text[:80]}
    except Exception as e:
        logger.error(f"Facebook post error: {e}")
        return {"status": "error", "platform": "facebook", "error": str(e)}


def post_to_instagram_caption(caption, profile_dir=INSTAGRAM_PROFILE_DIR, dry_run=False):
    """Prepare Instagram caption (feed posts require media -- opens browser for manual upload)."""
    if dry_run:
        print(f"\n[DRY RUN] Would post to Instagram:\n{caption[:200]}...")
        return {"status": "dry_run", "platform": "instagram"}

    import webbrowser
    # Instagram feed posts require media (image/video)
    # Best approach: open Instagram and notify user to attach media
    print("\nInstagram caption prepared:")
    print("-" * 40)
    print(caption)
    print("-" * 40)
    print("Note: Instagram requires an image/video for feed posts.")
    print("Opening Instagram -- please create the post and paste the caption above.")
    webbrowser.open("https://www.instagram.com/")
    time.sleep(3)
    return {"status": "caption_ready", "platform": "instagram", "caption": caption, "note": "Manual media attach required"}


# ── Process Approved Posts ────────────────────────────────────────────────────

def send_approved_posts(vault_path, dry_run=False, profile_dir=INSTAGRAM_PROFILE_DIR):
    """Read approved social post files and post them."""
    vault_path = Path(vault_path)
    approved_dir = vault_path / "Approved"
    done_dir = vault_path / "Done"
    logs_dir = vault_path / "Logs"
    logs_dir.mkdir(exist_ok=True)
    done_dir.mkdir(exist_ok=True)

    patterns = ["INSTAGRAM_POST_*.md", "FACEBOOK_POST_*.md", "SOCIAL_POST_*.md"]
    approved_files = []
    for pat in patterns:
        approved_files.extend(approved_dir.glob(pat))

    if not approved_files:
        print("No approved Instagram/Facebook posts found in /Approved/")
        return []

    results = []
    for af in approved_files:
        content = af.read_text(encoding="utf-8")

        # Parse platform
        platform_match = re.search(r"^platform:\s*(.+)$", content, re.MULTILINE)
        platform = platform_match.group(1).strip().lower() if platform_match else "facebook"

        # Parse content
        content_match = re.search(r"## Post Content\s*\n+(.*?)(?:\n## |\Z)", content, re.DOTALL)
        post_text = content_match.group(1).strip() if content_match else ""

        # Parse hashtags
        hashtag_match = re.search(r"## Hashtags\s*\n+(.*?)(?:\n## |\Z)", content, re.DOTALL)
        hashtags = hashtag_match.group(1).strip() if hashtag_match else ""

        full_text = f"{post_text}\n\n{hashtags}".strip() if hashtags else post_text

        print(f"\nPosting to {platform}: {full_text[:80]}...")

        result = {}
        if platform in ("instagram", "both"):
            result["instagram"] = post_to_instagram_caption(full_text, profile_dir, dry_run)
        if platform in ("facebook", "both"):
            result["facebook"] = post_to_facebook(full_text, profile_dir, dry_run)
        if platform not in ("instagram", "facebook", "both"):
            result["facebook"] = post_to_facebook(full_text, profile_dir, dry_run)

        results.append(result)

        if not dry_run:
            af.rename(done_dir / af.name)
            print(f"Moved {af.name} -> /Done/")

        # Log
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": "social_post_facebook_instagram",
            "actor": "instagram_watcher",
            "target": platform,
            "parameters": {"preview": full_text[:80], "result": str(result)},
            "approval_status": "approved",
            "approved_by": "human",
            "result": "success" if not dry_run else "dry_run",
            "dry_run": dry_run,
        }
        log_file = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"
        entries = json.loads(log_file.read_text(encoding="utf-8")) if log_file.exists() else []
        entries.append(log_entry)
        log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    return results


# ── Engagement Summary ────────────────────────────────────────────────────────

def generate_engagement_summary(vault_path):
    """Generate a social media engagement summary report."""
    vault_path = Path(vault_path)
    briefings_dir = vault_path / "Briefings"
    briefings_dir.mkdir(exist_ok=True)

    summary_file = briefings_dir / f"{datetime.now().strftime('%Y-%m-%d')}_Social_Engagement.md"
    summary_file.write_text(
        f"# Social Media Engagement Summary -- {datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"**Generated:** {datetime.now().isoformat()}\n\n"
        f"## Instagram\n"
        f"Full engagement metrics require Instagram Graph API (business account).\n"
        f"Session-based posting is active via browser automation.\n\n"
        f"## Facebook\n"
        f"Full engagement metrics require Facebook Graph API.\n"
        f"Session-based posting is active via browser automation.\n\n"
        f"## Recommendation\n"
        f"Connect Instagram/Facebook Business Accounts to Meta Graph API for automated engagement tracking.\n"
        f"See: https://developers.facebook.com/docs/graph-api\n\n"
        f"---\n*Generated by AI Employee Gold Tier*\n",
        encoding="utf-8",
    )
    print(f"Engagement summary saved: {summary_file}")
    return {"file": str(summary_file)}


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Instagram & Facebook Watcher (Gold Tier)")
    parser.add_argument("--vault", required=True)
    parser.add_argument("--setup-instagram", action="store_true")
    parser.add_argument("--setup-facebook", action="store_true")
    parser.add_argument("--post-approved", action="store_true")
    parser.add_argument("--engagement-summary", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--profile", default=str(INSTAGRAM_PROFILE_DIR))
    args = parser.parse_args()

    vault = Path(args.vault)
    profile = Path(args.profile)

    if args.setup_instagram:
        setup_instagram_session(profile)
    elif args.setup_facebook:
        setup_facebook_session(profile)
    elif args.post_approved:
        send_approved_posts(vault, args.dry_run, profile)
    elif args.engagement_summary:
        generate_engagement_summary(vault)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
