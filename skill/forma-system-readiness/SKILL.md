---
name: forma-system-readiness
description: Build, run, refresh, re-point and explain the read-only "is this system ready to launch?" dashboard for an Autodesk Forma / ACC (Autodesk Build) project, also called FOMO1. It pulls assets, issues, forms, documents and relationships through the APS APIs, follows the links from each asset to open issues and forms, rolls them up per system (GO / CONDITIONAL / NO-GO, lifecycle phases, dependency graph) and can show assets in a live APS 3D viewer on localhost. Use whenever someone mentions Forma or ACC system readiness, handover, commissioning or go/no-go status, issues or forms blocking an asset or system, "refresh the readiness dashboard", "switch it to project X", "which models should the viewer load", "serve it on localhost", a 403 or empty dashboard, a FOMO1 latest.json, or "FOMO1", even without asking for a dashboard. Not for one-off Forma API tasks, creating issues, or takeoff and cost work (use forma-aps-connect or takeoff-sync).
---

# Forma system readiness (FOMO1)

Answers one question for a Forma project: **which systems can launch, and what is blocking the rest?** From every asset it follows Forma's relationships and issue pins to the issues and forms that are still open, rolls them up per system, and renders a dashboard. The daily refresh is a plain Python script with **no AI**; Claude builds, tunes and explains it.

## Two builds: pick the right one first

| Situation | Use | Where |
|---|---|---|
| Run, set up, re-point or troubleshoot the dashboard with the lifecycle view and live 3D viewer (the usual case, also for colleagues) | **Live build** | The GitHub repo https://github.com/amalik84/Forma-Assets-System-Readiness-Visualization , cloned to a local folder outside OneDrive. Read its `GETTING_STARTED.md`, `CLAUDE.md` and `docs\08-decisions-and-open-questions.md` first |
| No repo access, or the GO / CONDITIONAL / NO-GO board, system dependencies, map-file grouping or a scheduled daily run is wanted | **FOMO1 bundle** | `assets/fomo1-app/` (Python) + `assets/dashboard-ui/` (optional React UI) in this skill |

If it is unclear which one is meant, ask. Both are standard-library Python, read only, 3-legged OAuth. `references/architecture.md` compares them side by side.

## Rules that keep this safe and correct

1. **Never ask for, accept, or echo secrets.** Client secret in `.env`, tokens in `.tokens\` (live) or `.secrets\` (FOMO1), all on the user's machine. If a secret is pasted into chat, say so and advise regenerating it in the APS portal after setup. Never write credentials into skill files, docs, examples or the HTML.
2. **Read only.** Only GET calls and read-style POSTs (search, batch-get, intersect). Raising issues is phase 2 (`references/writeback-phase2.md`), only on explicit request.
3. **Do not invent endpoints.** Use `references/api-reference.md` (it has a "Verified on real projects" section). There is no public Systems API; systems are derived.
4. **The data is what the signed-in user can see.** Say so whenever a dashboard is shared, and keep output in an access-controlled place. Project data never leaves the machine.
5. **Daily refresh stays AI-free and dependency-light.** pip is often blocked by corporate proxies; keep to the standard library. On Windows use `py` (the launcher) where `python` is only the Microsoft Store stub.
6. **Signing in is the user's step.** The login opens their browser on `localhost:8080`. Never type credentials for them.

## Working with the user

- **Claude Code on the user's own machine:** run the read-only steps yourself (whoami, refresh, render, tests), but leave the browser sign-in to the user and check the result afterwards.
- **User runs the commands (Cowork, chat, or a colleague's PC):** one step at a time. Say what the step does, give the exact command and the folder the prompt must be in, say what success looks like, then stop and wait for the pasted output.
- When there is an error, find the cause in `references/troubleshooting.md` before changing code.
- Report back short and concrete (British spelling, no em dashes): per-system table (status, assets, assets with links, blocking items), viewer coverage, and anything blocked with the exact error text and who can fix it. Say plainly when a system shows ready only because nothing is linked to it.

## Live build: set up for a new user

Follow `GETTING_STARTED.md` in the repo with the user, one step at a time. It covers who does what (user, APS app owner, account admin), then: clone, `.env`, `py src\auth.py login`, `py src\whoami.py`, `py src\survey.py` (system grouping), `.\refresh.ps1`, `.\serve.ps1`, `py src\survey.py --models` (viewer), and an error table. Most first-time problems are access, not code: project membership with Assets access, and the client ID under Account Admin > Custom Integrations with Document Management access. Send the user to their admin with the exact error text.

## Live build: everyday tasks

```powershell
cd <project folder>
.\refresh.ps1     # all fetch steps, readiness, render; one snapshot day per run (about 1 to 5 minutes)
.\serve.ps1       # http://127.0.0.1:8765 with the live viewer; Ctrl+C stops it
```

Power BI: `refresh.ps1` also writes `data\powerbi\` (CSV tables plus, on first run, `Forma System Readiness.pbip`). Open the `.pbip` in Power BI Desktop and refresh once (or `.\powerbi_refresh.ps1`); after that `refresh.ps1` refreshes the open project itself. `py src\export_powerbi.py --rebuild-project` regenerates the report (replaces the user's edits). The 3D viewer and graph exist only in the web dashboard.

Expired login ("Re-login needed", or no run for about 15 days): `py src\auth.py login`, user signs in, refresh again. Scripts blocked by policy: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

**Switch to another project**, in this order:
1. Set `FORMA_PROJECT_ID` (no `b.`) and `FORMA_HUB_ID` = the project's account ID in `.env`. A wrong hub only breaks Data Management, so it is easy to miss.
2. `py src\whoami.py` tests Assets, Issues, Forms, Relationships, Data Management one by one. The Data Management project listing may stay 403 while document lookups work; that is fine.
3. Choose the system grouping (`SYSTEM_ATTRIBUTE`): `py src\survey.py` lists category and every custom attribute with fill rate and distinct values, and marks good candidates. Ask before choosing. Values: a custom attribute's display name, `category` (top-level category, covers every asset), or `dataconnector` when the project uses Forma Systems (Assets > Systems tab). The regular API has no Systems endpoint; `dataconnector` keeps one daily Data Connector request (assets only, this project) and downloads just `assets_systems.csv` and `assets_system_memberships.csv`. It needs `APS_SCOPES=data:read data:write data:create`, a new login, and Data Connector access (account or project admin).
4. Set `FORMA_PROJECT_NAME`.
5. Choose the viewer models (`VIEWER_MODELS`): after one refresh, `py src\survey.py --models` ranks the most-linked viewable models and prints a `VIEWER_MODELS=` line. Serve, select a system and read the line under the viewer: it shows the assets found per model. Drop models with none (`references/model-matching.md`).
6. Refresh, serve, check one system and one asset against Forma.
7. Log the project, grouping, models and anything that failed in `docs\08-decisions-and-open-questions.md`.

Non-secret settings: `SYSTEM_ATTRIBUTE`, `ISSUE_DONE_STATUSES` (default `closed`), `FORM_DONE_STATUSES` (`submitted`), `MAX_DEPTH` (`2`), `VIEWER_MODELS`, `FORMA_ISSUE_URL` / `FORMA_FORM_URL` / `FORMA_ASSET_URL` (link formats, not yet verified). The lifecycle phase mapping is in `src\lifecycle.py`.

After a code change: `py -m unittest discover tests` must pass, re-render, check in the browser with a clean console, update the matching doc in `docs\`, keep `GETTING_STARTED.md` in step, and commit only when the user asks (`.env`, `.tokens\`, `data\`, `dashboard\` stay ignored).

## FOMO1 bundle: set up from scratch

**0. Prerequisites.** Python 3.10+ on Windows (`py --version`). An APS app with callback `http://localhost:8080/` and the Data Management + Forma/ACC APIs enabled, added under Account Admin > Custom Integrations (with Document Management access). The user must be a project member with access to Assets, Issues, Forms and Files.

**1. Put the app in place.** Copy `assets/fomo1-app/` to the user's working folder (outside OneDrive or other synced folders). The user copies `.env.example` to `.env` and fills in client ID, secret and callback URL themselves. Demo first: `py fomo1.py demo --open` (fake data, writes only to `output/demo/`).

**2. Sign in and find the project.**
```
py fomo1.py login          # browser opens; wait for "FOMO1 login complete"
py fomo1.py whoami
py fomo1.py hubs           # copy the hub id (b.xxxx) into FORMA_HUB_ID
py fomo1.py projects --hub b.xxxx   # copy the project id into FORMA_PROJECT_ID
py fomo1.py check          # every API should say OK
```
`Project → 403` in `check` is usually harmless (see troubleshooting).

**3. First run, then find the real systems.** `py fomo1.py probe` shows one full asset record and tests candidate systems endpoints. If the asset carries a system reference: `SYSTEM_GROUP_BY=asset_field` + `SYSTEM_FIELD_NAME` (+ `SYSTEMS_ENDPOINT`). If not (both real projects so far): `py fomo1.py run --open`, then `py fomo1.py fields` for fill rates. A good grouping is filled on most assets with about 3 to 50 distinct values. Otherwise `SYSTEM_GROUP_BY=map_file` with a `system_map.csv` exported from Forma, then `py fomo1.py regroup --open` (rebuilds from the last pull in seconds). Category is a stopgap; agree the real definition with the customer.

**4. Validate before trusting it.** Compare 5 to 10 assets with Forma (asset > Relationships, plus issues on its linked drawings). Look at the blocker paths: at `MAX_DEPTH=3` one shared model can attribute every issue pinned on it to each linked asset; consider `MAX_DEPTH=2`. Report data-quality findings, such as "most open issues are not linked to any asset"; that is often the real headline.

**5. System dependencies (optional).** Edit `systems.json` with `["upstream","downstream"]` pairs using exact system names, then `py fomo1.py render --open` (no Forma calls).

**6. React dashboard (optional).** In `assets/dashboard-ui/`: `npm install`, `npm run build`, then `py fomo1.py render --open`. Without Node or npm the plain-HTML fallback is used automatically. `npm run test:logic` checks the model and graph layout.

**7. Schedule the daily refresh.** `.\schedule_daily.ps1 -Time 06:00`, test with `Start-ScheduledTask -TaskName "FOMO1 Daily Refresh"`. One successful run per day keeps the 15-day refresh token alive.

**8. Day to day.** Answer straight from `latest.json`: NO-GO systems and why, overdue blockers, assets with no links, changes since the last snapshot, what a stricter or looser rule would do. Cite item labels and Forma links. Adjust rules in `.env` (`references/readiness-rules.md`) rather than code.

## References (read on demand)

| File | When |
|---|---|
| `references/discovery-and-scope.md` | Starting a new project: definitions, scope, questions for the customer |
| `references/architecture.md` | How the pieces fit; FOMO1 vs live build |
| `references/authentication.md` | Login, tokens, scopes, `.env`, permissions |
| `references/api-reference.md` | Endpoints, ID rules, paging, rate limits, verified findings |
| `references/readiness-rules.md` | What counts as ready, system grouping, traversal, `systems.json` |
| `references/dashboard-spec.md` | FOMO1 UI and `latest.json` schema; live build dashboard |
| `references/model-matching.md` | Choosing viewer models for the live build |
| `references/troubleshooting.md` | Any error, odd number, network or PowerShell problem |
| `references/writeback-phase2.md` | Only if asked to raise or change Forma data |

## Extending

- Rules and statuses: `.env` first. FOMO1: `ISSUE_CLOSED_STATUSES`, `FORM_OPEN_STATUSES`, `READY_ASSET_STATUSES`, `MAX_DEPTH`, `REL_DOMAINS`. Live build: see its settings above.
- FOMO1 UI logic lives in `dashboard-ui/src/lib/model.ts` and `layout.ts` (plain TypeScript with a Node test); keep components thin.
- Give the user whole replacement files with their path, not scattered fragments.
- The live build is MIT-0 (no attribution needed). Encourage users to send fixes and ideas back to the shared repo (issue, Discussion or pull request, see its `CONTRIBUTING.md`) instead of keeping a private copy; check a pull request contains no secrets, real IDs or customer names.
- Keep `references/` (and, for the live build, its `docs\`) in step with every change.
