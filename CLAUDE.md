# Forma System Readiness Dashboard

Main instruction file for any AI agent working in this project. Read this first, then the files in `docs/` that the task needs.

Personal or machine-specific rules, if any, live in `CLAUDE.local.md` (git-ignored). New users: start with `GETTING_STARTED.md`.

---

## 1. What we are building

A daily-refreshed, read-only dashboard that answers one question per system in a Forma (ACC Build) project:

> **Is this system ready to launch?**

A system is **ready** when none of its assets has an open issue or open form linked to it, directly or through any chain of relationships (asset > document > issue, asset > form > issue, and so on).

The dashboard lets a user click a system, see its assets, click an asset and see every referenced item (issues, forms, documents) with status and a link back to Forma.

Full brief: `docs/01-project-brief.md`.

## 2. Ground rules

1. **Read only in phase 1.** Only `GET` requests, plus the `POST` endpoints that are pure searches (Relationships search, Assets batch-get). No create, update or delete calls. Raising issues from the dashboard is phase 2.
2. **The production script must not use AI.** Claude helps write and maintain the code. The script itself is plain Python, runs unattended every morning and produces the dashboard without calling any LLM.
3. **Permissions come from the user's login.** We use 3-legged OAuth, so the script only sees what the signed-in Forma user is allowed to see. Never work around this with a 2-legged token unless a decision is recorded in `docs/08-decisions-and-open-questions.md`.
4. **Secrets stay in `.env` and `.tokens/`.** Never print, log, commit or copy client secret, access tokens or refresh tokens. Never paste them into chat output, test fixtures or the dashboard.
5. **Never invent API endpoints or fields.** `docs/04-api-reference.md` lists what we use. If something is marked `VERIFY`, check the official APS docs (https://aps.autodesk.com/developer/documentation) or a real response before relying on it, then update the doc.
6. **Save real API responses as fixtures** in `data/raw/` (git-ignored) when exploring, so we design against real data, not guesses. Project data is customer data: it never leaves this machine.
7. **Deliverables** (screenshots, exported reports, slides about this project) go outside the repository (see `CLAUDE.local.md` if present). Code stays here.

## 3. Tech stack

- Python 3.12 (`py` launcher on this machine)
- **Standard library only** (`urllib`, `json`, `http.server`, `string.Template`). pip downloads are blocked by the corporate network, and no dependencies keeps the daily job simple. Don't add packages without logging a decision in doc 08.
- Output: one static `dashboard/index.html` plus `dashboard/data.json`. No server needed to view it.
- Scheduling: Windows Task Scheduler, once a day.

## 4. Project layout

```
forma-system-readiness/
  CLAUDE.md                 this file
  GETTING_STARTED.md        guide for new users (keep it in step with any change)
  refresh.ps1               run every fetch step, readiness and render (one snapshot day)
  serve.ps1                 serve the dashboard with the live viewer on http://127.0.0.1:8765
  .env                      secrets (git-ignored)
  .env.example              template without secrets
  docs/                     context files for agents and humans
  src/
    config.py               loads .env
    auth.py                 3-legged OAuth, token storage, refresh
    whoami.py               signed-in user, hubs, projects, checks .env IDs
    survey.py               suggests SYSTEM_ATTRIBUTE and VIEWER_MODELS for a new project
    aps_client.py           HTTP wrapper: base URL, paging, retries, rate limits
    fetch/                  one module per API: hubs, assets, relationships, issues, forms, documents
    model.py                build the system > asset > reference graph
    readiness.py            readiness rules
    render.py               write data.json and index.html
    lifecycle.py            phase of each reference (design / execution / handover)
    serve.py                local server for the dashboard + token for the live viewer
    export_powerbi.py       readiness as Power BI tables (data/powerbi/*.csv) + project on first run
    powerbi_project.py      generates the Power BI project: TMDL model, measures, theme, 3 report pages
    run_daily.py            entry point for the scheduled job
  templates/dashboard.html  page template; render.py embeds the data
  assets/fonts/             Artifakt fonts for the dashboard
  dashboard/                generated output (git-ignored)
  data/raw/                 saved API responses (git-ignored)
  .tokens/                  token cache (git-ignored)
  logs/                     run logs (git-ignored)
  tests/
```

## 5. Context files

| File | Read it when |
|---|---|
| `docs/01-project-brief.md` | Always, for scope and success criteria |
| `docs/02-architecture.md` | Designing or changing any module |
| `docs/03-auth-aps.md` | Touching login, tokens or scheduling |
| `docs/04-api-reference.md` | Calling any Forma/APS endpoint |
| `docs/05-data-model-and-readiness.md` | Building the graph or readiness logic |
| `docs/06-dashboard-spec.md` | Working on the UI |
| `docs/07-build-guide.md` | Working out what to do next |
| `docs/08-decisions-and-open-questions.md` | Before making any design choice. Log new decisions here. |

## 6. How to work in this project

- Follow the steps in `docs/07-build-guide.md` in order. Finish and verify one step before starting the next.
- After each step, tick it off in the build guide and note anything learned in the relevant doc.
- Prefer small, readable functions over clever code. The people maintaining this are technical specialists, not full-time developers.
- Every API module handles paging, `429` rate limits (respect `Retry-After`) and `401` (refresh token once, then fail clearly).
- Run tests with `py -m unittest discover tests` (standard library `unittest`). Test pure functions on small hand-made fixtures, not live API calls.
- Log to `logs/run-YYYY-MM-DD.log`: counts per entity, durations, warnings. Never log tokens or full response bodies with personal data.
- British spelling in docs and UI text. No em dashes.
