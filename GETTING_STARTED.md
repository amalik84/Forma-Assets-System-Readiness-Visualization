# Getting started: run the readiness dashboard on your own Forma project

About 30 to 60 minutes the first time, most of it waiting for access. You do not need to be a developer: every step is one command, and each one says what to do next if something is missing.

**Easiest route:** install the Claude skill in `skill/forma-system-readiness/` and ask Claude to "set up the readiness dashboard for my project". It follows this guide with you.

---

## Before you start: who does what

| Who | What | Once or per project |
|---|---|---|
| **You** | Windows PC with Python from python.org (check: `py --version` shows 3.10 or newer) and Git | Once |
| **You** | A Forma (ACC) login that is a **member of the project** with access to Assets, Issues, Forms and Files | Per project |
| **App owner** (you, or whoever owns the APS app) | An APS app at https://aps.autodesk.com/myapps with callback URL exactly `http://localhost:8080/` and the Data Management + Autodesk Construction Cloud APIs ticked | Once |
| **Account admin** of the Forma account | Add the app's **client ID** under Account Admin > Custom Integrations, with **Document Management** access | Per account |

Use your own APS app if you can. Sharing one app means sharing its client secret; if you do, send it privately (never by email or chat logs that are kept) and rotate it when people leave.

Ports `8080` (login) and `8765` (dashboard) must be free on your PC.

---

## 1. Get the code

```powershell
cd $HOME\Documents
git clone https://github.com/amalik84/Forma-Assets-System-Readiness-Visualization.git forma-system-readiness
cd forma-system-readiness
```
Keep it out of OneDrive or other synced folders: the data and login tokens should stay on your PC.

If PowerShell later says "running scripts is disabled", run this once per window:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 2. Create your settings file

```powershell
copy .env.example .env
notepad .env
```
Fill in `APS_CLIENT_ID` and `APS_CLIENT_SECRET` from the APS app. Leave the rest for now. Never share or commit `.env` (git already ignores it).

## 3. Log in and find your project

```powershell
py src\auth.py login
```
Your browser opens. Sign in with your Autodesk account. **Success:** the browser says "Logged in" and the terminal says "Logged in. Tokens saved".

Now set the project. In `.env`:
- `FORMA_PROJECT_ID`: open the project in Forma in the browser; the address contains `projects/<project id>` (a long ID with dashes). Copy that ID (no `b.` in front).
- `FORMA_HUB_ID`: the ID of the Forma **account** that holds the project. `py src\whoami.py` lists the hubs you can see; otherwise ask your account admin.
- `FORMA_PROJECT_NAME`: any name for the dashboard header.

Then check access:
```powershell
py src\whoami.py
```
**Success:** your name, and under "API access for project" `OK` for Assets, Issues, Forms and Relationships. A `403` on the Data Management line alone is usually fine (document names still work). For any other `403`, see the table at the end.

## 4. Choose how assets are grouped into systems

Forma has no public "systems" API, so the dashboard groups assets by an asset field you choose.
```powershell
py src\survey.py
```
It lists every option with how many assets have it filled in. Pick one marked "good candidate" and put it in `.env`, for example:
```
SYSTEM_ATTRIBUTE=category
```
`category` (the top-level asset category) always works. A custom attribute is better if your project has a real "System" field. Agree with your team what "system" should mean.

**Your project uses Forma Systems (Assets > Systems tab)?** Use those instead: the regular API does not offer them, but the Data Connector does.
```
SYSTEM_ATTRIBUTE=dataconnector
APS_SCOPES=data:read data:write data:create
```
Then log in again (`py src\auth.py login`, needed for the new scopes). Your Forma role must be allowed to use the Data Connector (account admin, or project admin for this project). The first `.\refresh.ps1` creates one small daily Data Connector request (assets only, this project) and waits for its first run, which can take some minutes. After that each refresh just downloads the latest two system files, so it stays fast. Nested systems show as "Parent > Child".

## 5. First refresh

```powershell
.\refresh.ps1
```
Takes 1 to 5 minutes. **Success:** a green "Refresh done" line. If a step fails, the red line names it; read the lines just above it.

## 6. Open the dashboard

```powershell
.\serve.ps1
```
Your browser opens http://127.0.0.1:8765. Stop it with Ctrl+C. The 3D viewer stays empty until step 7.

**Check it against Forma:** pick one system and one or two assets, and compare their linked issues and forms with what Forma shows. The dashboard sees exactly what your login can see.

## 7. Optional: the 3D viewer

The viewer highlights assets in the project's models. It only works when asset names come from a model (they end in an element id, such as `Door - Interior - Double [1263119]`).

```powershell
py src\survey.py --models
```
It shows which systems have matchable asset names and the most-linked viewable models, and prints a `VIEWER_MODELS=...` line. Copy that line into `.env`, then:
```powershell
.\refresh.ps1
.\serve.ps1
```
Select a system. The line under the viewer says how many of its assets were found, and how many assets each model contains. Remove the models that contain none from `VIEWER_MODELS`, and refresh once more.

## 7b. Optional: the same results in Power BI

Every `.\refresh.ps1` also writes the results as Power BI tables to `data\powerbi\`. The first time, it also creates a Power BI project there.

1. Install Power BI Desktop (free, from Microsoft) if you do not have it.
2. Open `data\powerbi\Forma System Readiness.pbip` in Power BI Desktop.
3. The first time, click **Refresh now** in the yellow bar (or run `.\powerbi_refresh.ps1`) to load the data.

**Success:** three pages (Overview, Assets and lifecycle, Blocking items) with the same numbers as the web dashboard. After that, `.\refresh.ps1` also updates Power BI whenever the project is open. The 3D viewer and the relationship graph stay in the web dashboard: Power BI has no built-in visuals for them.

Your own changes to the report are kept. To get a newer report version from the repository, run `py src\export_powerbi.py --rebuild-project` (this replaces your changes), then refresh.

## 8. Day to day

- `.\refresh.ps1` whenever you want fresh data, then `.\serve.ps1` to look at it.
- If you have not refreshed for about 15 days, the login expires: run `py src\auth.py login` again.
- Sharing results: `dashboard\index.html` opens by double-clicking (without the 3D viewer). It contains the project data your login can see, so share it only in an access-controlled place.

## 9. Other settings in .env

| Setting | What it does | Default |
|---|---|---|
| `ISSUE_DONE_STATUSES` | Issue statuses that count as done (comma list) | `closed` |
| `FORM_DONE_STATUSES` | Form statuses that count as done | `submitted` |
| `MAX_DEPTH` | How many link steps to follow from an asset | `2` (3 can pull in every issue pinned on a shared model) |
| `FORMA_ISSUE_URL`, `FORMA_FORM_URL`, `FORMA_ASSET_URL` | "Open in Forma" link formats | acc.autodesk.com formats, not yet verified everywhere |

Which item types count as Design, Execution or Handover is set in `src\lifecycle.py`.

---

## If something goes wrong

| You see | Do this |
|---|---|
| `Missing ...\.env` or `... is not set in .env` | Steps 2 and 3 |
| `Not logged in` / `Re-login needed` | `py src\auth.py login` |
| Login page shows an error about the redirect or callback | The APS app's callback URL must be exactly `http://localhost:8080/`, same as in `.env` |
| `Hubs (0)` with "You don't have permission to access this API" | The account admin has not added the client ID under Custom Integrations, or not for this account |
| Assets `403` "not a project member or does not have access to the assets product" | Ask the project admin to add you with Assets access |
| Data Management `403` everywhere | `FORMA_HUB_ID` is not the project's account, or Document Management access is missing on the integration |
| `SYSTEM_ATTRIBUTE '...' not found` | Run `py src\survey.py` and choose again (step 4) |
| `python` says "install from the Microsoft Store" | Use `py`, or install Python from python.org |
| `pip` errors | Nothing to install: the project uses only standard Python |
| Viewer says "needs your login" | Open the dashboard with `.\serve.ps1`, not by double-clicking |
| A system shows "ready" but nothing is linked to its assets | Not a real "ready": nobody has linked issues or forms to those assets in Forma |

More detail: `skill/forma-system-readiness/references/troubleshooting.md`. How it works: `docs/`.
