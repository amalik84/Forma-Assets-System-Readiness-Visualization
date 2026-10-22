# 06 · Dashboard Spec & Snapshot Schema

## UI (output/dashboard.html: one file, works offline, no AI)

Two renderers share the same `latest.json`:
- **React + shadcn/ui build** (`dashboard-ui/`, Vite + TypeScript + Tailwind). Build once with `npm install && npm run build`; Python then injects each day's data into `dist/index.html`. Layout: KPI cards, gate matrix, launch-dependency graph, Tabs (Blocking items / Assets), side column with verdict summary, trend and details.
- **Plain-HTML fallback** (`app/dashboard.py`) used automatically when the React build doesn't exist. No topology graph in the fallback.

The description below applies to both unless noted.

1. **Header**: project name, refresh time, how systems are grouped.
2. **KPI row**: systems ready (x/y), assets clear, open issues on assets (30-day sparkline), open forms on assets (sparkline), open issues not linked to any asset.
3. **Systems list** (left): one card per system with a READY / NOT READY pill, a progress bar (% assets clear) and counts. Not-ready systems are sorted first. A toggle shows not-ready systems only.
4. **Assets table** (right): assets in the selected system, sorted by blockers. Columns: asset, category, status, readiness, linked counts. Has a search box.
5. **Asset references panel**: grouped by Status rule / Issues / Forms / Documents / Linked assets / RFIs. Each row shows the label (deep link into Forma), a status pill and the **reference path** with due date and type.

Colours: green = ready/ok, red = blocking, amber = warning / no access.

## Snapshot (`output/latest.json`, also `snapshots/snapshot_YYYY-MM-DD.json`)
```json
{
  "meta": {"projectName": "...", "projectId": "uuid", "hubId": "b.uuid", "generatedAt": "2026-10-21T06:00:04",
           "groupBy": "custom_attribute", "systemAttribute": "System", "maxDepth": 3,
           "issueClosed": ["closed"], "formOpen": ["inProgress", "inReview"], "formsApi": "v2",
           "apiCalls": 312, "durationSec": 74.2},
  "summary": {"systems": 5, "systemsReady": 1, "assets": 30, "assetsReady": 13, "openIssues": 20,
              "openForms": 11, "unlinkedOpenIssues": 5, "totalIssues": 48, "totalForms": 20},
  "systems": [{"name": "HVAC", "ready": false, "assetCount": 12, "readyCount": 4, "openIssues": 10,
               "openForms": 5, "warnings": 1, "assetIds": ["..."]}],
  "assets": {"<assetId>": {
      "id": "...", "name": "AHU-01", "description": "...", "category": "AHU", "status": "Installed",
      "system": "HVAC", "ready": false, "blockers": 2, "warnings": 0, "url": "https://acc.autodesk.com/...",
      "refs": [{"kind": "issue", "id": "...", "label": "Issue #42 Insulation damaged", "status": "open",
                "state": "blocking", "due": "2026-11-03", "type": "Commissioning", "assignee": "...",
                "path": ["AHU-01", "AHU submittal Rev B.pdf", "Issue #42 Insulation damaged"], "url": "..."}]}},
  "topology": {"feeds": [["Electrical", "HVAC"]], "unmatched": [], "placeholder": false, "source": "systems.json"},
  "history": [{"date": "...", "systems": "5", "systemsReady": "1", "openIssues": "20", "...": "..."}]
}
```
`kind` ∈ `issue | form | document | asset | rfi | status`; `state` ∈ `blocking | warning | unknown | ok`.

## Ideas for Claude to help with (on request)
- Upload `latest.json` → "Which systems are blocked and by what? Top 10 overdue blocking issues?"
- Render an interactive view of the snapshot in chat for a meeting.
- Add filters (by assignee, issue type, due date), a CSV export or a print view to `dashboard.py`.
- Compare two snapshots (what changed since yesterday).

## Deep links
Templates live in `.env` (`LINK_ISSUE`, `LINK_ASSET`, `LINK_FORM`, `LINK_DOCUMENT`) with `{projectId}` and `{id}` placeholders. Open one item in Forma, copy its URL and adjust the template if it differs.

## Live build dashboard (version 2, October 2026)

Static page `dashboard\index.html`, data embedded, Autodesk palette (black and white, Warm Slate surfaces, tertiaries for status only, one Hello Yellow highlight on the selected row) and Artifakt fonts.

| Area | Content |
|---|---|
| Header + tiles | Project, data time, signed-in user; systems ready / not ready / unknown; open issues and forms linked to assets |
| Left | Systems (not ready first, "no links at all" called out), assets of the selected system with search and filters |
| Lifecycle band | Three phase cards (Design, Execution, Handover and operations) with blocking / unknown / done / reference bars; click to focus. System: asset count per lifecycle step (click to filter). Asset: stepper with the current step |
| Relationship graph | SVG around the selected asset: phase zones, lines follow the real path (asset > document > issue), documents as squares, other link types grouped ("Meeting item × 5"), max 14 nodes per zone |
| Live 3D viewer | APS Viewer, models from `VIEWER_MODELS`. Selected asset coloured by readiness and zoomed to; selected system: all its assets coloured; clicking an element selects its asset |
| Inspector | Selected system, asset or node; related information list with "Open in Forma" links |

States: ready, not ready, unknown (linked item not returned by the API), unassigned (`(no system)` bucket, never ready). Asset to model element matching is by name; see `model-matching.md`.
