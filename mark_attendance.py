"""
Mark attendance on mrei.icloudems.com from an Excel file.

Prerequisites:
    1. Run save_session.py at least once and have a valid auth_state.json
    2. Prepare an Excel file (see data/sample_attendance.xlsx)

Usage:
    python mark_attendance.py
"""

from playwright.sync_api import sync_playwright, expect
import pandas as pd
import time
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# ====================== CONFIG ======================
EXCEL_FILE = "data/sample_attendance.xlsx"

# Date as shown on the portal (DD/MM/YYYY)
TARGET_DATE = "01/10/2026"

# Exact time slot text that appears on the weekly timetable card
# Example: "09:50 - 10:40"
TARGET_TIME_SLOT = "09:50 - 10:40"

# Optional: exact text of the lecture topic from the dropdown
# Leave as None if you want to select it manually or skip
LECTURE_TOPIC = None

# Keep False while testing so you can watch the browser
HEADLESS = False

# Column names expected in Excel (case-insensitive)
# Prefer enrollment_no / prn. Name is used as fallback.
# ====================================================


def load_attendance(excel_path: str) -> dict:
    """Return dict: key (enrollment or name) → is_present (bool)"""
    df = pd.read_excel(excel_path)
    df.columns = [str(c).strip().lower() for c in df.columns]

    present_map = {}
    for _, row in df.iterrows():
        enrollment = str(row.get("enrollment_no") or row.get("prn") or row.get("enrollment") or "").strip()
        name = str(row.get("name") or row.get("full_name") or "").strip()

        raw = str(row.get("present") or row.get("status") or "").strip().lower()
        is_present = raw in {"yes", "y", "1", "p", "present", "true"}

        if enrollment:
            present_map[enrollment] = is_present
        if name:
            present_map[name.lower()] = is_present

    return present_map


def human_confirm(page, message: str):
    """Pause and ask the user before any irreversible action."""
    ts = datetime.now().strftime("%H%M%S")
    screenshot_path = f"screenshots/confirm_{ts}.png"
    page.screenshot(path=screenshot_path, full_page=True)
    print(f"\n{'='*60}")
    print(f"CONFIRMATION REQUIRED")
    print(f"{message}")
    print(f"Screenshot saved: {screenshot_path}")
    print(f"{'='*60}")
    ans = input("Type 'yes' to continue, anything else to abort → ").strip().lower()
    if ans != "yes":
        raise RuntimeError("User aborted the operation.")


def mark_attendance():
    present_map = load_attendance(EXCEL_FILE)
    print(f"Loaded {len(present_map)} student records from {EXCEL_FILE}")

    Path("screenshots").mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            slow_mo=150,
            args=["--start-maximized"] if not HEADLESS else []
        )
        context = browser.new_context(
            storage_state="auth_state.json",
            no_viewport=True
        )
        page = context.new_page()

        try:
            # ---------- 1. Open dashboard ----------
            page.goto("https://mrei.icloudems.com/corecampus/admin/admin_index1.php")
            page.wait_for_load_state("networkidle")
            page.screenshot(path="screenshots/01_dashboard.png")

            # ---------- 2. Go to Attendance ----------
            page.get_by_text("Attendance", exact=True).first.click()
            page.wait_for_url("**/attendanceTakenSearch.php", timeout=15000)
            page.wait_for_load_state("networkidle")
            page.screenshot(path="screenshots/02_weekly.png")

            # ---------- 3. (Optional) set date ----------
            # Uncomment and adjust if you need to change the week
            # date_input = page.locator("input[type='text']").first
            # date_input.fill(TARGET_DATE)
            # page.get_by_role("button", name="Search").click()
            # page.wait_for_load_state("networkidle")

            # ---------- 4. Click the correct time-slot card ----------
            # Look for a card that contains the target time slot text
            slot_locator = page.locator("div").filter(has_text=re.compile(re.escape(TARGET_TIME_SLOT)))
            if slot_locator.count() == 0:
                raise RuntimeError(f"Could not find time slot: {TARGET_TIME_SLOT}")

            # Prefer the orange "Update" or blue "Take" button
            button = slot_locator.first.get_by_role("button", name=re.compile(r"Update|Take", re.I))
            button.click()
            page.wait_for_url("**/attendanceTaken.php", timeout=15000)
            page.wait_for_load_state("networkidle")
            page.screenshot(path="screenshots/03_marking_page.png")

            # ---------- 5. Select lecture topic (optional) ----------
            if LECTURE_TOPIC:
                # There are usually two dropdowns; the second is the syllabus topic
                selects = page.locator("select")
                if selects.count() >= 2:
                    selects.nth(1).select_option(label=LECTURE_TOPIC)
                    time.sleep(0.5)

            # ---------- 6. Mark checkboxes ----------
            rows = page.locator("table tbody tr")
            total = rows.count()
            print(f"Found {total} students on the marking page")

            marked_present = 0
            marked_absent = 0

            for i in range(total):
                row = rows.nth(i)

                # Column indices observed from your screenshot:
                # 0: Sr.No | 1: Full Name | 2: Profile | 3: QR | 4: Registration Status
                # 5: Enrollment No/PRN | 6: Admno | 7: Division | 8: Present checkbox | 9: Remark
                try:
                    name = row.locator("td").nth(1).inner_text().strip()
                    enrollment = row.locator("td").nth(5).inner_text().strip()
                except Exception:
                    print(f"  Skipping row {i} (could not read cells)")
                    continue

                key = enrollment if enrollment in present_map else name.lower()
                should_be_present = present_map.get(key)

                if should_be_present is None:
                    print(f"  ⚠️  No data for → {name} ({enrollment}) – left unchanged")
                    continue

                checkbox = row.locator("input[type='checkbox']").first
                currently_checked = checkbox.is_checked()

                if should_be_present and not currently_checked:
                    checkbox.check()
                    marked_present += 1
                    print(f"  ✓ PRESENT  → {name} ({enrollment})")
                elif not should_be_present and currently_checked:
                    checkbox.uncheck()
                    marked_absent += 1
                    print(f"  ✗ ABSENT   → {name} ({enrollment})")
                else:
                    status = "PRESENT" if currently_checked else "ABSENT"
                    print(f"  • already {status} → {name}")

            print(f"\nSummary: {marked_present} newly marked present, {marked_absent} newly marked absent")

            # ---------- 7. Human confirmation before submit ----------
            human_confirm(
                page,
                "All checkboxes have been set according to the Excel file.\n"
                "Ready to click the final Save / Submit button on the portal?"
            )

            # ---------- 8. Final submit ----------
            # Inspect the real button text on the page and adjust if needed
            submit_btn = page.get_by_role("button", name=re.compile(r"Save|Submit|Update Attendance", re.I))
            if submit_btn.count() == 0:
                # Fallback: look for any primary button at the bottom
                submit_btn = page.locator("button.btn-primary, input[type='submit']").last

            submit_btn.first.click()
            page.wait_for_load_state("networkidle")
            page.screenshot(path="screenshots/04_success.png")
            print("\n✅ Attendance submitted successfully!")

        except Exception as e:
            page.screenshot(path="screenshots/error.png", full_page=True)
            print(f"\n❌ Error occurred: {e}")
            print("Screenshot saved → screenshots/error.png")
            raise
        finally:
            # Refresh the saved session
            context.storage_state(path="auth_state.json")
            browser.close()


if __name__ == "__main__":
    mark_attendance()
