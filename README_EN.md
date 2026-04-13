# Dalang ERP (Open Source)

[中文说明请见 README.md](README.md)

A **web-based inventory and operations MVP** for small and medium businesses: materials and revisions, BOMs, stock, procurement (receipts/invoices), RFQs, suppliers, sales orders (Taobao/WooCommerce sync plus manual orders), production plans, basic reports, and Excel import/export.

Stack: **FastAPI + SQLite + Jinja2**, single process. **Source-available** under a **custom personal/internal-use license** — you may **not sell** the software as a product or offer **paid third-party hosting/SaaS** where this app is the main deliverable. See [LICENSE](LICENSE). **No warranty** — see [DISCLAIMER.md](DISCLAIMER.md). Do **not** commit real business data or API secrets.

---


## Requirements

- **Python** 3.10+ (3.11+ recommended). Install from [https://www.python.org/downloads/](https://www.python.org/downloads/) and enable **“Add python.exe to PATH”** on Windows.
- OS: Windows, Linux, or macOS.
- Disk space for SQLite and `uploads/`.

---

## Installation (step-by-step)

**Project root** means the directory that contains `app/`, `requirements.txt`, and `README.md`. Run all commands from there.

### Check Python

```powershell
python --version
```

On some Windows setups, use `py --version` instead.

### Get the code

```powershell
git clone <your-repo-url> dalang-erp
cd dalang-erp
```

Or unpack a ZIP into e.g. `D:\dalang-erp` and open a terminal **in that folder** (on Windows: File Explorer address bar → type `powershell` → Enter).

### Virtual environment (recommended)

**Windows — two options**

*If `Activate.ps1` fails in PowerShell (common: “running scripts is disabled”), use **CMD + `activate.bat`** below — it avoids PowerShell’s execution policy entirely.*

**A) PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

If `python` is not found, try `py -m venv .venv`.

**B) Command Prompt (CMD) — often easiest on Windows**

1. In File Explorer, open your project root, type `cmd` in the address bar, press Enter.
2. Run:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -U pip
pip install -r requirements.txt
```

You should see `(.venv)` at the start of the prompt. You can run `uvicorn` from this same window.

**PowerShell fixes if you prefer `.ps1` activation**

- Temporary (current window only):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

- Persistent for your user account (one-time):

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Confirm with `Y` if prompted, then run `.\.venv\Scripts\Activate.ps1` again.

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

### Run the app

With the venv activated (PowerShell or CMD):

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Web UI: [http://127.0.0.1:8000/ui](http://127.0.0.1:8000/ui)
- OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Stop with `Ctrl+C`.

On first run the app creates `data/inventory.db`, default **system options** (units, tax presets, etc.), and a placeholder company row. It does **not** ship demo transactions. It also does **not** seed **material categories** — open **Categories** in the UI and create categories **before** adding materials.

### Optional: start on Windows sign-in / boot

**Yes, you can.** The usual approach is **Task Scheduler** running a batch file (no PowerShell activation needed).

1. Create `.venv` and `pip install -r requirements.txt` first; confirm a manual `uvicorn` run works.
2. Use **`scripts\start_server.bat`**: it `cd`s to the repo root, activates `.venv`, and runs `uvicorn` **without `--reload`** (better for an always-on instance; restart the task/process after code changes).
3. Open **Task Scheduler** (`taskschd.msc`) → **Create Task**:
   - **Trigger**: prefer **At log on** for your Windows user (so Python and `.venv` resolve reliably). **At startup** as SYSTEM often fails to find user-local Python unless you configure the account carefully.
   - **Action** → **Start a program**:
     - **Program/script**: full path to `scripts\start_server.bat` (e.g. `D:\erp-opensource\scripts\start_server.bat`).
     - **Start in (optional)**: project root (e.g. `D:\erp-opensource`).
4. Test with **Run** on the task; open [http://127.0.0.1:8000/ui](http://127.0.0.1:8000/ui).

You will normally keep a **console window** open for logs; closing it stops the server. For headless operation, auto-restart, HTTPS, etc., consider NSSM, a proper Windows service, or Docker.

---

## Usage overview

1. **Categories**: Create material categories and code prefixes first.
2. **Settings → Company**: Buyer/legal entity for PDFs and RFQs.
3. **Materials / revisions**, **Products / BOMs**, **Inventory**, **Procurement**, **Sales**, **Integrations** as needed.

More detail: in-app **Tutorial** page.

---

## Repository layout

```
.
├── app/
├── scripts/
├── data/
├── uploads/
├── image/
├── requirements.txt
├── LICENSE
├── DISCLAIMER.md
├── README.md
└── README_EN.md
```

---

## Security notes

- Keep `.gitignore` effective; do not track `data/*.db`, secrets, or real uploads.
- Taobao / WooCommerce secrets belong in the **local database** via the UI only.

---

## License

This is **not** an OSI-style “open source” license that permits unrestricted commercial exploitation. It is a **custom license**: **personal / single-organization internal use**; **no selling** the software (or a derivative where it is the primary product) **for a fee**; **no paid third-party hosting/SaaS** where this software is the **main offering**. Gratis redistribution of source must include the full [LICENSE](LICENSE) and may not violate those rules.

There is **no single standard license name** that exactly means “only for yourself, cannot sell this software” — projects typically use a **custom LICENSE** file (as here) or ask a lawyer to draft terms. Chinese text is primary in [LICENSE](LICENSE) with an English summary; get legal advice for high-stakes use.

**Commercial resale, paid deployment-for-hire as a software product, OEM, etc.** require **written permission** from the copyright holder(s).

---

## Disclaimer (short)

The software is provided **“as is”** without warranty. You are responsible for compliance, backups, and third-party API terms. Full text: [DISCLAIMER.md](DISCLAIMER.md).

---

## FAQ

**Why no demo data?**  
To avoid leaking real business information; you enter or import your own.

**Why are material categories empty?**  
The open-source package **intentionally** does not ship preset categories. Create them under **Categories** after a fresh install or after deleting `data/inventory.db`.

**PowerShell won’t run `Activate.ps1` / “scripts are disabled”?**  
That is Windows **execution policy**. Use **CMD** with `.venv\Scripts\activate.bat` (see **Virtual environment** above), or run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that PowerShell window before activating.

**Can we use this in production?**  
Running it **inside your company** for your **own** operations is generally in scope. **Selling** the app, or **charging external clients** mainly for hosting/deploying **this** software, is **not** allowed without **written permission**. Evaluate backups, security, and compliance yourself; when in doubt, consult a lawyer.
