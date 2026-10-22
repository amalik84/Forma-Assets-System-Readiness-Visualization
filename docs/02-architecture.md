# 02. Architecture

## Overview

```
 ┌──────────────┐   once    ┌───────────────────┐
 │ User browser │ ────────> │ APS authorize page │  3-legged login
 └──────────────┘           └─────────┬─────────┘
                                      │ code to http://localhost:8080/
                            ┌─────────▼─────────┐
                            │ src/auth.py       │  exchanges code, stores refresh token in .tokens/
                            └─────────┬─────────┘
                                      │ every morning (Task Scheduler)
                            ┌─────────▼─────────┐
                            │ src/run_daily.py  │
                            └─────────┬─────────┘
          ┌──────────────┬────────────┼─────────────┬──────────────┐
          ▼              ▼            ▼             ▼              ▼
     fetch/hubs     fetch/assets  fetch/relat.  fetch/issues   fetch/forms   (+ documents)
          └──────────────┴────────────┼─────────────┴──────────────┘
                            ┌─────────▼─────────┐
                            │ model.py          │  graph: system > asset > references (multi-level)
                            │ readiness.py      │  ready / not ready / unknown + reasons
                            └─────────┬─────────┘
                            ┌─────────▼─────────┐
                            │ render.py         │  dashboard/data.json + dashboard/index.html
                            └───────────────────┘
```

## Design choices

| Choice | Why |
|---|---|
| Python script, no server | Simple to run and schedule, no hosting, no AI at runtime |
| Static HTML + JSON | Open by double-clicking, easy to share as a file, can move to a hosted page later |
| 3-legged OAuth | Data respects the signed-in user's Forma permissions (the "permission levels" point from the call) |
| Fetch everything per project, then join locally | Fewer API calls than walking asset by asset; easier to test against saved fixtures |
| Snapshot per day in `data/raw/<projectId>/YYYY-MM-DD/` | Lets us debug yesterday's result and later show trends |

## Run sequence (daily)

1. Load `.env`, refresh access token with the stored refresh token. Save the new refresh token straight away (they are single use).
2. Resolve hub and project from `.env` (`FORMA_HUB_ID`, `FORMA_PROJECT_ID`). If missing, list them and stop with a clear message.
3. Fetch systems, assets, categories, asset statuses.
4. Fetch issues (all statuses) and forms (all statuses) for the project.
5. Fetch relationships for the project (sync or search, see API reference).
6. Fetch document metadata only for documents that appear in relationships.
7. Build graph, compute readiness, render.
8. Write log. Exit code 0 on success, non-zero on failure so Task Scheduler shows it.

## Failure handling

- Refresh token expired or revoked: stop, log "re-login needed: run `py src/auth.py login`", keep yesterday's dashboard and mark it stale with the date.
- One API fails (for example Forms 403): continue, mark affected references as `unknown`, show a banner in the dashboard. Never show a system as ready when data is missing.
