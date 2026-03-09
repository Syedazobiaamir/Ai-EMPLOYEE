#!/usr/bin/env python3
"""Instagram & Facebook Watcher - Gold Tier (Meta Graph API + Browser fallback)."""
import argparse, json, logging, os, time
from datetime import datetime
from pathlib import Path
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("InstagramWatcher")

INSTAGRAM_PROFILE_DIR = Path("config/instagram_profile")
FACEBOOK_PROFILE_DIR  = Path("config/facebook_profile")
GRAPH_API_BASE        = "https://graph.facebook.com/v21.0"


def load_meta_credentials():
    creds = {}
    env_path = Path("config/.env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                creds[k.strip()] = v.strip()
    return {
        "page_access_token": creds.get("FACEBOOK_PAGE_ACCESS_TOKEN", os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")),
        "page_id":           creds.get("FACEBOOK_PAGE_ID", os.getenv("FACEBOOK_PAGE_ID", "")),
        "ig_user_id":        creds.get("INSTAGRAM_USER_ID", os.getenv("INSTAGRAM_USER_ID", "")),
    }


def graph_api_configured():
    c = load_meta_credentials()
    return bool(c["page_access_token"] and c["page_id"])


def post_to_facebook_graph(text, dry_run=False):
    if dry_run:
        print(f"\n[DRY RUN] Facebook Page (Graph API):\n{text[:300]}")
        return {"status": "dry_run", "platform": "facebook"}
    c = load_meta_credentials()
    resp = requests.post(
        f"{GRAPH_API_BASE}/{c['page_id']}/feed",
        data={"message": text, "access_token": c["page_access_token"]},
        timeout=30
    )
    data = resp.json()
    if resp.status_code == 200:
        logger.info(f"Facebook posted: {data.get('id')}")
        return {"status": "success", "platform": "facebook", "post_id": data.get("id")}
    logger.error(f"Facebook Graph error: {data.get('error')}")
    return {"status": "error", "platform": "facebook", "error": str(data.get("error"))}


def post_to_instagram_graph(caption, image_url=None, dry_run=False):
    if dry_run:
        print(f"\n[DRY RUN] Instagram (Graph API):\n{caption[:300]}")
        return {"status": "dry_run", "platform": "instagram"}
    c = load_meta_credentials()
    ig_id, token = c["ig_user_id"], c["page_access_token"]
    if not ig_id:
        return {"status": "skipped", "reason": "INSTAGRAM_USER_ID not set in .env"}
    img = image_url or os.getenv("INSTAGRAM_IMAGE_URL", "")
    if not img:
        return {"status": "skipped", "reason": "No image URL. Set INSTAGRAM_IMAGE_URL in .env"}
    r1 = requests.post(f"{GRAPH_API_BASE}/{ig_id}/media",
        data={"image_url": img, "caption": caption, "access_token": token}, timeout=30)
    if r1.status_code != 200:
        return {"status": "error", "error": str(r1.json().get("error"))}
    r2 = requests.post(f"{GRAPH_API_BASE}/{ig_id}/media_publish",
        data={"creation_id": r1.json().get("id"), "access_token": token}, timeout=30)
    if r2.status_code == 200:
        return {"status": "success", "platform": "instagram", "post_id": r2.json().get("id")}
    return {"status": "error", "error": str(r2.json().get("error"))}


def setup_instagram_session(profile_dir=INSTAGRAM_PROFILE_DIR):
    from playwright.sync_api import sync_playwright
    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    print("\nOpening Instagram login...")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir), headless=False, slow_mo=500)
        page = ctx.new_page()
        page.goto("https://www.instagram.com/accounts/login/",
                  wait_until="domcontentloaded", timeout=60000)
        print("Waiting for login (3 min)...")
        try:
            page.wait_for_function(
                "() => !window.location.href.includes('/accounts/login')",
                timeout=180000)
            time.sleep(3)
            print(f"Instagram session saved: {profile_dir}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            ctx.close()


def setup_facebook_session(profile_dir=FACEBOOK_PROFILE_DIR):
    from playwright.sync_api import sync_playwright
    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    print("\nOpening Facebook login...")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir), headless=False, slow_mo=500)
        page = ctx.new_page()
        page.goto("https://www.facebook.com/login",
                  wait_until="domcontentloaded", timeout=60000)
        print("Waiting for login (3 min)...")
        try:
            page.wait_for_function(
                "() => !window.location.href.includes('/login') && "
                "!window.location.href.includes('checkpoint')",
                timeout=180000)
            time.sleep(3)
            print(f"Facebook session saved: {profile_dir}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            ctx.close()


def send_approved_posts(vault_path, dry_run=False, profile_dir=INSTAGRAM_PROFILE_DIR):
    vault_path = Path(vault_path)
    approved_dir = vault_path / "Approved"
    done_dir = vault_path / "Done"
    done_dir.mkdir(exist_ok=True)

    files = []
    for pat in ["INSTAGRAM_POST_*.md", "FACEBOOK_POST_*.md", "SOCIAL_POST_*.md"]:
        files.extend(approved_dir.glob(pat))

    if not files:
        print("No approved Instagram/Facebook posts found in /Approved/")
        return []

    use_graph = graph_api_configured()
    print(f"Method: {'Meta Graph API' if use_graph else 'Browser UI fallback'}")

    results = []
    for af in files:
        content = af.read_text(encoding="utf-8").strip()
        fname = af.name.upper()
        platform = "facebook" if "FACEBOOK" in fname else "instagram" if "INSTAGRAM" in fname else "both"

        print(f"\nPosting to {platform}: {content[:80]}...")
        result = {}

        if use_graph:
            if platform in ("facebook", "both"):
                result["facebook"] = post_to_facebook_graph(content, dry_run)
            if platform in ("instagram", "both"):
                result["instagram"] = post_to_instagram_graph(content, dry_run=dry_run)
        else:
            if platform in ("facebook", "both"):
                result["facebook"] = _browser_post_facebook(content, FACEBOOK_PROFILE_DIR, dry_run)
            if platform in ("instagram", "both"):
                result["instagram"] = {
                    "status": "caption_ready", "caption": content,
                    "note": "Set FACEBOOK_PAGE_ACCESS_TOKEN + INSTAGRAM_USER_ID for auto-posting"
                }

        results.append(result)
        print(f"Result: {result}")

        if not dry_run:
            dest = done_dir / af.name
            if dest.exists():
                dest = done_dir / f"{af.stem}_{int(time.time())}{af.suffix}"
            try:
                af.rename(dest)
                print("Moved to /Done/")
            except Exception as e:
                logger.error(f"Could not move: {e}")

        log_dir = vault_path / "Logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"
        logs = json.loads(log_file.read_text(encoding="utf-8")) if log_file.exists() else []
        logs.append({
            "timestamp": datetime.now().isoformat(),
            "action_type": "social_post",
            "actor": "instagram_watcher",
            "target": platform,
            "parameters": {"preview": content[:80], "api": "graph" if use_graph else "browser"},
            "approval_status": "approved",
            "result": "success" if not dry_run else "dry_run",
        })
        log_file.write_text(json.dumps(logs, indent=2), encoding="utf-8")

    return results


def _browser_post_facebook(text, profile_dir, dry_run=False):
    if dry_run:
        print(f"[DRY RUN] Browser Facebook: {text[:100]}")
        return {"status": "dry_run"}
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir), headless=False, slow_mo=600,
                args=["--no-sandbox", "--window-size=1280,900"])
            page = ctx.new_page()
            page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            for sel in ["div[aria-label='Create a post']", "[placeholder=\"What's on your mind?\"]"]:
                try:
                    el = page.locator(sel).first
                    el.wait_for(state="visible", timeout=5000)
                    el.click()
                    break
                except Exception:
                    continue
            page.wait_for_timeout(2000)
            for sel in ["div[contenteditable='true'][role='textbox']", "[contenteditable='true']"]:
                try:
                    el = page.locator(sel).last
                    el.wait_for(state="visible", timeout=8000)
                    el.click()
                    page.keyboard.type(text, delay=30)
                    break
                except Exception:
                    continue
            page.wait_for_timeout(1000)
            page.get_by_role("button", name="Post").last.click()
            page.wait_for_timeout(3000)
            ctx.close()
            return {"status": "success", "platform": "facebook"}
    except Exception as e:
        logger.error(f"Browser error: {e}")
        return {"status": "error", "error": str(e)}


def generate_engagement_summary(vault_path):
    vault_path = Path(vault_path)
    summary = {}
    if graph_api_configured():
        c = load_meta_credentials()
        try:
            r = requests.get(f"{GRAPH_API_BASE}/{c['page_id']}",
                params={"fields": "name,fan_count,followers_count",
                        "access_token": c["page_access_token"]}, timeout=15)
            if r.status_code == 200:
                summary["facebook"] = r.json()
        except Exception as e:
            summary["error"] = str(e)
    else:
        summary["note"] = "Configure FACEBOOK_PAGE_ACCESS_TOKEN for live data"
    out = vault_path / "Briefings" / f"{datetime.now().strftime('%Y-%m-%d')}_Social_Engagement.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(
        f"# Social Engagement\n\n```json\n{json.dumps(summary, indent=2)}\n```\n",
        encoding="utf-8")
    print(f"Saved: {out}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Instagram & Facebook Watcher (Gold Tier)")
    parser.add_argument("--vault", required=True)
    parser.add_argument("--setup-instagram",    action="store_true")
    parser.add_argument("--setup-facebook",     action="store_true")
    parser.add_argument("--post-approved",      action="store_true")
    parser.add_argument("--engagement-summary", action="store_true")
    parser.add_argument("--dry-run",            action="store_true")
    parser.add_argument("--profile",            default=None)
    args = parser.parse_args()
    vault = Path(args.vault)
    if args.setup_instagram:
        setup_instagram_session(Path(args.profile) if args.profile else INSTAGRAM_PROFILE_DIR)
    elif args.setup_facebook:
        setup_facebook_session(Path(args.profile) if args.profile else FACEBOOK_PROFILE_DIR)
    elif args.post_approved:
        send_approved_posts(vault, args.dry_run)
    elif args.engagement_summary:
        generate_engagement_summary(vault)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
