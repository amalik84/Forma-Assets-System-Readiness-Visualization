# 02 · Architecture

## Big picture

```
 ┌───────────────┐   one-time browser login   ┌──────────────────────────┐
 │  Team member  │ ─────────────────────────▶ │ Autodesk sign-in (APS)   │
 └───────────────┘                            └────────────┬─────────────┘
                                                           │ code → tokens
 ┌─────────────────────────── local PC / VM ───────────────▼──────────────┐
 │  .env (client id/secret, project, rules)    .secrets/tokens.json       │
 │                                                                         │
 │  Task Scheduler 06:00 ──▶ python fomo1.py run                           │
 │      auth.py        refresh token → access token                        │
 │      aps_client.py  GET + retries + throttling + pagination             │
 │      collector.py   project, assets, issues, forms, relationships, docs │
 │      readiness.py   build graph → walk from each asset → ready/blocked  │
 │      dashboard.py   one self-contained HTML file                        │
 │                                                                         │
 │  output/dashboard.html   output/latest.json   output/history.csv        │
 └──────────────────────────────────┬──────────────────────────────────────┘
                                    │ copy/sync (optional)
                         SharePoint / Teams folder (restricted)
```

Claude (this project) is used to **build, extend and explain** the code and to **analyse `latest.json`**. Claude is not in the daily run path.

## Data flow (one run)
1. **Auth** – load `tokens.json`; if the access token is expired, refresh it (new refresh token saved).
2. **Project** – resolve name via Data Management (`b.` IDs).
3. **Asset reference data** – categories, statuses, custom attribute definitions (to find the `System` attribute key).
4. **Assets** – all active assets (v2, cursor paging, with custom attributes).
5. **Issues** – all non-deleted issues + issue types; keep `linkedDocuments` (pushpins).
6. **Forms** – v2 (beta) with automatic fallback to v1.
7. **Relationships** – domain-wide search for each domain in `REL_DOMAINS` (falls back to per-asset search).
8. **Document names** – Data Management item lookups for the document URNs found.
9. **Readiness** – graph walk + rules → snapshot.
10. **Outputs** – `dashboard.html`, `latest.json`, `snapshots/snapshot_YYYY-MM-DD.json`, `history.csv`, `logs/fomo1.log`.

## Folder layout (after copying the bundled assets to a working folder)
```
FOMO1/
├─ app/                 runs on the user's PC
│  ├─ .env              (secret, never share)    .env.example (safe template)
│  ├─ config.py  simplehttp.py  auth.py  aps_client.py  collector.py  readiness.py  dashboard.py
│  ├─ fomo1.py          CLI: login | whoami | hubs | projects | check | fields | run | render | demo
│  ├─ systems.json      system dependency pairs for the graph
│  ├─ schedule_daily.ps1
│  └─ output/           dashboard.html, latest.json, raw_latest.json, history.csv, snapshots/, logs/
└─ dashboard-ui/        React + shadcn/ui source; `npm run build` -> dist/index.html
```

## Design choices
| Choice | Why |
|---|---|
| Python standard library only | Runs on any Windows PC with no `pip install` (corporate proxies often block PyPI). |
| 3-legged OAuth | Data respects the user's Forma permissions; matches the custom integration with a callback URL. |
| Static HTML with data embedded | Opens anywhere, no server, no AI, easy to share in a restricted folder. |
| Normalised "raw" layer → snapshot | Collector and readiness rules are independent; `demo` mode tests the dashboard with fake data. |
| Config in `.env` | Statuses, grouping, depth and links change without code edits. |

## Running unattended
- The scheduled task runs as the signed-in Windows user. Refresh tokens last ~15 days, so one successful run per day keeps the session alive indefinitely. If the PC is off for over 15 days, run `python fomo1.py login` again.
- For a server/VM without a human login, consider an **APS Secure Service Account** (a robot user with its own Forma membership) as a phase 1.5 upgrade.

## Two builds of the same idea

| | FOMO1 bundle (`assets/fomo1-app`, `assets/dashboard-ui`) | Live build (this repository) |
|---|---|---|
| Purpose | Portable: copy to a new machine or customer and set up from scratch | The maintained version, validated on two projects |
| Entry points | `python fomo1.py login / check / probe / fields / run / regroup / render / demo` | `refresh.ps1`, `serve.ps1`, `py src\whoami.py`, `py src\auth.py login` |
| Output | `output\dashboard.html` + `latest.json`, GO / CONDITIONAL / NO-GO, system dependency graph (`systems.json`) | `dashboard\index.html`, lifecycle band, per-asset relationship graph, live APS 3D viewer |
| Snapshots | `snapshots\snapshot_YYYY-MM-DD.json` | `data\raw\<projectId>\<YYYY-MM-DD>\` (one folder per project) |
| Viewer | none | `serve.py` on 127.0.0.1:8765 hands the browser a token; models from `VIEWER_MODELS` |
| Docs | `references\` in this skill | `CLAUDE.md` + `docs\01` to `docs\08` in the project (doc 08 = every decision) |

Both are standard-library Python, read only, 3-legged, no AI at runtime. Ideas move between them by hand: for example the live build could adopt FOMO1's `systems.json` dependencies and `map_file` grouping, and FOMO1 could adopt the live viewer and the `MAX_DEPTH=2` lesson.
