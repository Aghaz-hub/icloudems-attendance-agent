"""
One-time (or occasional) script to capture a logged-in browser session.
Run this whenever the saved session expires.

Usage:
    python save_session.py
"""

from playwright.sync_api import sync_playwright
import time
from pathlib import Path

def main():
    print("=" * 60)
    print("iCloudEMS Session Saver")
    print("=" * 60)
    print()
    print("1. A browser window will open.")
    print("2. Click 'Staff Login'.")
    print("3. Enter your mobile/email and click SIGN IN.")
    print("4. Enter the Google Authenticator code.")
    print("5. Wait until you see the main dashboard.")
    print("6. Come back here and press Enter.")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=200,
            args=["--start-maximized"]
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        page.goto("https://mrei.icloudems.com/corecampus/index.php")
        page.wait_for_load_state("networkidle")

        # Click Staff Login button
        try:
            page.get_by_role("button", name="Staff Login").click(timeout=10000)
        except Exception:
            # Fallback selector
            page.locator("text=Staff Login").click()

        print("\n>>> Browser is ready. Complete the login (including OTP).")
        input(">>> Press ENTER here AFTER you are fully logged in and see the dashboard... ")

        # Optional: click Attendance once so the session is warm
        try:
            page.get_by_text("Attendance", exact=True).first.click(timeout=5000)
            time.sleep(2)
        except Exception:
            print("(Could not auto-click Attendance – that's OK)")

        # Save storage state
        Path(".").mkdir(exist_ok=True)
        context.storage_state(path="auth_state.json")
        print("\n✅ Session saved successfully → auth_state.json")
        print("   Keep this file private. It is already in .gitignore.")

        browser.close()

if __name__ == "__main__":
    main()
