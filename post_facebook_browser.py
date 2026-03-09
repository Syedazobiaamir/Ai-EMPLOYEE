#!/usr/bin/env python3
"""Facebook Browser UI Post — waits for login then auto-posts."""

from playwright.sync_api import sync_playwright
from pathlib import Path

# instagram_profile has a valid Facebook session too
FACEBOOK_PROFILE_DIR = Path("config/instagram_profile")

TEXT = """Our AI Employee just posted to Instagram automatically!

Every morning it autonomously:
- Reads WhatsApp & Gmail
- Drafts replies and invoices
- Posts to LinkedIn, Instagram & Facebook
- Audits Odoo accounting
- Generates CEO briefing

Built with Claude Code in 72 hours for the #AIEmployee hackathon.

This post was written and published automatically by the AI Employee.

#AI #Automation #AIEmployee #ClaudeAI #SmallBusiness #Pakistan"""


def main():
    FACEBOOK_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(FACEBOOK_PROFILE_DIR),
            headless=False, slow_mo=600,
            args=["--no-sandbox", "--window-size=1280,900"]
        )
        page = browser.new_page()
        print("Opening Facebook...")
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # Wait for home feed — check for nav bar presence
        logged_in = False
        try:
            page.wait_for_selector("[aria-label='Facebook']", timeout=8000)
            logged_in = True
        except Exception:
            pass

        if not logged_in:
            print("\n>>> LOG IN TO FACEBOOK IN THE BROWSER <<<")
            print("Waiting up to 3 minutes for login...")
            try:
                page.wait_for_selector("[aria-label='Facebook']", timeout=180000)
            except Exception:
                pass
            page.wait_for_timeout(3000)

        print(f"Logged in! URL: {page.url}")
        page.screenshot(path="fb_post_step1.png")

        # Click "What's on your mind?" box
        print("\nClicking post box...")
        clicked = False
        for sel in [
            "div[aria-label='Create a post']",
            "[aria-label=\"What's on your mind?\"]",
            "div[role='button']:has-text(\"What's on your mind\")",
        ]:
            try:
                el = page.locator(sel).first
                el.wait_for(state="visible", timeout=5000)
                el.click()
                print(f"Clicked: {sel}")
                clicked = True
                break
            except Exception:
                continue

        if not clicked:
            print("Post box not found — trying fallback...")
            try:
                page.get_by_placeholder("What's on your mind?").click()
                clicked = True
            except Exception:
                pass

        page.wait_for_timeout(2000)

        # Type post text
        print("Typing post...")
        for sel in [
            "div[contenteditable='true'][role='textbox']",
            "[contenteditable='true']",
        ]:
            try:
                el = page.locator(sel).last
                el.wait_for(state="visible", timeout=8000)
                el.click()
                page.keyboard.type(TEXT, delay=20)
                print("Text typed!")
                break
            except Exception:
                continue

        page.wait_for_timeout(1000)
        page.screenshot(path="fb_post_step2.png")
        print("Screenshot: fb_post_step2.png")

        # Click Post button
        print("\nClicking Post...")
        try:
            page.get_by_role("button", name="Post").last.click()
            print("Post clicked!")
        except Exception as e:
            print(f"Post button: {e}")

        page.wait_for_timeout(5000)
        page.screenshot(path="fb_post_final.png")
        print("Screenshot: fb_post_final.png")
        print("\nDone! Closing in 5s...")
        page.wait_for_timeout(5000)
        browser.close()


if __name__ == "__main__":
    main()
