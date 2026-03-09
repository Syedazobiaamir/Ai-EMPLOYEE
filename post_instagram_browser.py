#!/usr/bin/env python3
"""
Instagram Browser UI Post — Gold Tier Demo
==========================================
Posts to Instagram via browser automation (no API required).
Instagram feed posts require an image. Uses ai_employee_logo.png.

Run: python -X utf8 post_instagram_browser.py
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import time
import os

INSTAGRAM_PROFILE_DIR = Path("config/instagram_profile")
IMAGE_PATH = Path("config/instagram_post.jpg").resolve()

CAPTION = """Excited to share: our AI Employee is now fully autonomous!

Every morning it:
- Reads WhatsApp & Gmail messages
- Drafts replies and invoices
- Posts to LinkedIn, Facebook & Instagram
- Audits Odoo accounting
- Generates a CEO briefing

Built with Claude Code + Playwright + Odoo in 72 hours for the #AIEmployee hackathon.

This post was written and published automatically by the AI Employee.

#AI #Automation #AIEmployee #FTE #ProductivityHack #ClaudeAI #NoCode #SmallBusiness"""


def post_to_instagram():
    print("\n" + "="*60)
    print("  Instagram Browser UI Post — AI Employee Demo")
    print("="*60)
    print(f"\nImage: {IMAGE_PATH}")
    print(f"Caption: {CAPTION[:80]}...\n")

    if not IMAGE_PATH.exists():
        print(f"ERROR: Image not found at {IMAGE_PATH}")
        print("Place an image at config/ai_employee_logo.png and retry.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(INSTAGRAM_PROFILE_DIR),
            headless=False,
            slow_mo=500,
            args=["--no-sandbox", "--window-size=1280,900"],
        )

        page = browser.new_page()
        print("Opening Instagram...")
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # Check if logged in
        if "login" in page.url or "accounts" in page.url:
            print("\nNot logged in — please log in to Instagram in the browser.")
            print("Waiting up to 2 minutes for login...")
            try:
                page.wait_for_url("https://www.instagram.com/", timeout=120000)
            except Exception:
                pass
            page.wait_for_timeout(3000)

        print(f"Loaded: {page.url}")
        page.screenshot(path="insta_step1.png")
        print("Screenshot: insta_step1.png")

        # Step 1: Click the Create button in the sidebar
        print("\nStep 1: Clicking Create...")
        try:
            # The Create button contains text "Create" in the sidebar
            page.locator("a:has(span:text-is('Create'))").click()
            print("Clicked Create via span")
        except Exception:
            try:
                page.locator("[aria-label='New post']").click()
                print("Clicked via aria-label")
            except Exception as e:
                print(f"Create button: {e}")
        page.wait_for_timeout(2000)
        page.screenshot(path="insta_step2.png")
        print("Screenshot: insta_step2.png")

        # Step 2: Click "Post" from dropdown — use nth(1) since 2 matches
        print("\nStep 2: Clicking Post option...")
        try:
            # "Post Post" is the actual Post menu item (nth 1 of the 2 matches)
            page.get_by_role("link", name="Post").nth(1).click()
            print("Clicked Post (nth 1)")
        except Exception as e:
            print(f"Post nth(1): {e}")
            try:
                page.locator("a[role='link']").filter(has_text="Post").last.click()
                print("Clicked Post via filter")
            except Exception as e2:
                print(f"Post fallback: {e2}")
        page.wait_for_timeout(3000)
        page.screenshot(path="insta_step3.png")
        print("Screenshot: insta_step3.png")

        # Step 3: Upload image via file chooser
        print("\nStep 3: Uploading image...")
        try:
            with page.expect_file_chooser(timeout=15000) as fc_info:
                page.get_by_role("button", name="Select from computer").click()
            fc_info.value.set_files(str(IMAGE_PATH))
            print(f"Uploaded: {IMAGE_PATH.name}")
        except Exception as e:
            print(f"File chooser error: {e}")
            print(f"Please manually select: {IMAGE_PATH}")
        page.wait_for_timeout(4000)
        page.screenshot(path="insta_step4.png")
        print("Screenshot: insta_step4.png")

        # Step 4: Next (crop)
        print("\nStep 4: Next (crop)...")
        try:
            page.get_by_role("button", name="Next").click()
            print("Next clicked")
        except Exception as e:
            print(f"Next crop: {e}")
        page.wait_for_timeout(2000)

        # Step 5: Next (filter)
        print("Step 5: Next (filter)...")
        try:
            page.get_by_role("button", name="Next").click()
            print("Next clicked")
        except Exception as e:
            print(f"Next filter: {e}")
        page.wait_for_timeout(2000)
        page.screenshot(path="insta_step5.png")
        print("Screenshot: insta_step5.png")

        # Step 6: Type caption
        print("\nStep 6: Typing caption...")
        try:
            cap = page.locator("div[aria-label='Write a caption...']").first
            cap.wait_for(state="visible", timeout=10000)
            cap.click()
            page.keyboard.type(CAPTION, delay=15)
            print("Caption typed!")
        except Exception as e:
            print(f"Caption: {e} — type manually in browser")
        page.wait_for_timeout(2000)
        page.screenshot(path="insta_step6.png")
        print("Screenshot: insta_step6.png")

        # Step 7: Share
        print("\nStep 7: Clicking Share...")
        try:
            page.locator("div[role='dialog'] div[role='button']:has-text('Share')").last.click()
            print("Share clicked!")
        except Exception:
            try:
                page.get_by_role("button", name="Share").last.click()
                print("Share clicked (fallback)!")
            except Exception as e:
                print(f"Share: {e} — click Share manually in browser")

        page.wait_for_timeout(5000)
        page.screenshot(path="insta_final.png")
        print("Screenshot: insta_final.png")
        print("\n✅ Post submitted! Check insta_final.png to confirm.")
        print("Browser closing in 5 seconds...")
        page.wait_for_timeout(5000)
        browser.close()


if __name__ == "__main__":
    post_to_instagram()
