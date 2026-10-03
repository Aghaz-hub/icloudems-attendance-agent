# iCloudEMS Attendance Agent (Manav Rachna)

Automated attendance marking for **mrei.icloudems.com** using Playwright.

> ⚠️ **Important**
> - You must have written institutional permission to use automation.
> - Never commit `auth_state.json`, `.env`, or any student data that contains personal information.
> - Always keep the final human confirmation step enabled.

---

## Features

- Reuses a saved browser session (no password stored in code)
- Reads attendance from a simple Excel file
- Marks Present / Absent checkboxes automatically
- Takes screenshots at every major step
- Human confirmation before the final Submit
- Optional TOTP support for fully automatic OTP (advanced)

---

## Quick Start

### 1. Clone & install

```bash
git clone <your-repo-url>
cd icloudems-attendance-agent

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Capture a logged-in session (one-time)

```bash
python save_session.py
```

- A browser opens.
- Click **Staff Login** → enter mobile/email → enter Google Authenticator code.
- When you see the dashboard, come back to the terminal and press **Enter**.
- `auth_state.json` is created (already ignored by git).

### 3. Prepare your Excel file

Copy `data/sample_attendance.xlsx` and edit it:

| enrollment_no   | name             | present |
|-----------------|------------------|---------|
| 2K26CSU01NN002  | Anurag Chaubey   | Yes     |
| 2K26CSU01NN004  | Shridula Nainwal | No      |
| 2K26CSU01NN007  | Kavya Vani       | Yes     |

- Prefer **Enrollment No / PRN** (most reliable).
- `present` accepts: Yes / No / Y / N / 1 / 0 / P / A / Present / Absent

### 4. Configure the target class

Open `mark_attendance.py` and edit the top config section:

```python
EXCEL_FILE = "data/sample_attendance.xlsx"
TARGET_DATE = "01/10/2026"
TARGET_TIME_SLOT = "09:50 - 10:40"   # exact text shown on the weekly page
LECTURE_TOPIC = None                 # or the exact dropdown text
HEADLESS = False                     # keep False while testing
```

### 5. Run

```bash
python mark_attendance.py
```

The script will:
1. Open the portal with the saved session
2. Navigate to Attendance → correct time slot
3. Mark the checkboxes according to your Excel
4. Pause and ask you to type `yes` before the final Submit
5. Save screenshots in the `screenshots/` folder

---

## Project Structure

```
icloudems-attendance-agent/
├── save_session.py          # Capture login session
├── mark_attendance.py       # Main attendance marker
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   └── sample_attendance.xlsx
└── screenshots/             # Auto-generated
```

---

## Optional: Fully automatic OTP

If you have the Base32 secret from Google Authenticator:

1. Copy `.env.example` → `.env`
2. Put the secret in `TOTP_SECRET=...`
3. You can extend `save_session.py` or `mark_attendance.py` to generate the code with `pyotp`.

**Only do this on a machine you fully control.**

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Session expired | Re-run `python save_session.py` |
| Time slot not found | Check exact text of `TARGET_TIME_SLOT` (including spaces) |
| Wrong students marked | Verify Enrollment No in Excel matches the portal exactly |
| Selectors broken | Portal UI changed → use `playwright codegen` to update selectors |
| Checkbox not clicking | Increase `slow_mo` or add `page.wait_for_timeout(500)` |

---

## Security Notes

- `auth_state.json` contains your session cookies → treat it like a password.
- Never push student attendance data that contains personal information to a public repo.
- Keep the human confirmation step. It is your safety net.

---

## License

Private / internal use only. Do not distribute without institutional approval.
