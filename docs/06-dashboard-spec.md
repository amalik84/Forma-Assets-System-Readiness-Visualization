# 06. Dashboard specification

One static page, `dashboard/index.html`, built by `py src/render.py` from `templates/dashboard.html`. Opens by double-clicking. No external CDNs, so it works offline and does not leak project data.

Implementation notes (2026-10-21):
- The data is **embedded** in the page (browsers block reading a local `data.json` from a `file://` page). `dashboard/data.json` is written too, for other tools.
- Demo project A page size: about 2.9 MB (6,516 assets, references for 876).
- Fonts: Artifakt Legend Bold (headings), Artifakt Element Regular and Semi Bold (text), copied from `assets/fonts/` to `dashboard/fonts/` when present. The font files are not in the repository (`assets/fonts/README.md`); without them the page uses Arial.
- Colours: Autodesk Black and White, Warm Slate surfaces, Slate for secondary text and dividers. Status uses tertiaries for function only: Morning = ready, Dusk = not ready / blocking, Dawn = unknown, Slate = no system / reference. Pills always carry a text label. Hello Yellow is used once: the edge of the selected row, on black.
- The `(no system)` bucket opens with "Only assets with links" ticked, and lists are paged by 200.
- Links back to Forma: documents use the `webView` link from Data Management (verified format). Issue, form and asset links are built from `FORMA_ISSUE_URL`, `FORMA_FORM_URL`, `FORMA_ASSET_URL` in `.env`. **These three formats are not verified yet** (open question 11).
- References other than issues, forms and documents (schedule activities, meeting items, sheets...) show only their type, no name: we do not call those APIs.
- Preview while developing: `.claude/launch.json` in the knowledge folder has a `forma-dashboard` config that serves `dashboard/` on http://localhost:8765.

## Version 2 (2026-10-21): lifecycle, graph, live viewer

Inspired by a concept mock-up (a static demo with illustrative data and images). We kept its ideas, not its look: the page stays on the Autodesk palette and type.

### Layout

| Area | Content |
|---|---|
| Header + tiles | Project, data time, signed-in user; systems ready / not ready / unknown, open issues and forms linked to assets |
| Left | Systems list, then assets of the selected system (search, readiness, category, only with links) |
| Centre top: **Lifecycle band** | Three phase cards (Design, Execution, Handover and operations) with counts and a blocking / unknown / done / reference bar. Click a phase to focus graph and list. Below: for a system, how many assets sit at each lifecycle step (click a step to filter assets; pick another status set if the system mixes them); for an asset, a stepper showing its current step |
| Centre left: **Relationship graph** | SVG graph of the selected asset. Asset at the top, references placed in three phase zones, lines follow the real path (asset > document > issue). Issues and forms are circles, documents squares, other link types grouped per type ("Meeting item × 5"). Max 14 nodes per zone, the rest in "+ N more". Filters: all / issues and forms / documents / other links |
| Centre right: **Live 3D viewer** | APS Viewer with the models from `VIEWER_MODELS`. Selected asset is coloured by readiness, selected and zoomed to. Selected system: all its assets in the models are coloured. Clicking an element in the model selects its asset in the dashboard |
| Right: **Inspector** | Selected system, asset or graph node: status, lifecycle step, type, due date, why it is linked, Open in Forma. Below: related information list, filtered by phase and graph filter |

### Lifecycle

- **Asset lifecycle** = the asset's status in its Forma status set (`status-step-sets`), for example Doors: Specified > Planned > Ordered > Delivered > Installed > Checked. Saved per asset as `lifecycleSetId` + `lifecycleStep`.
- **Phase of a reference** is derived from its type in `src/lifecycle.py` (Forma has no phase field). Design: documents, models, sheets, RFIs, submittals, markups, issue types Design / Coordination / Interface Queries / Viewpoints. Handover: issue type Commissioning, form template type commissioning. Everything else: Execution. Adjust the tables per project.

### Live viewer

- Needs the local server: `py src/serve.py`, then http://127.0.0.1:8765. Double-clicking `index.html` still works, without the viewer (it says how to start it).
- `serve.py` listens on 127.0.0.1 only, refuses other Host headers (DNS rebinding), sends no CORS headers, and hands the browser your current 3-legged token at `/api/token`. **The token is never written into the HTML** (checked 2026-10-21).
- Viewer library loads from `developer.api.autodesk.com` (needs internet).
- `VIEWER_MODELS` in `.env`: comma-separated lineage URNs. `py src/fetch/models.py` resolves each to its latest version and checks the translation; failed translations are skipped.
- Asset to element matching: by name. Forma asset names created from a model are the element names (`Door - Interior - Double [1263119]`). Demo project A with Arch_demo v28 + MEP-central v6 + Struc v2: **2,032 of 6,516 assets** found; B10: 126 of 257.
- Several copies of each model exist in the project. We picked the copies most linked to issues and assets. Three Struc_demo copies failed translation in Forma.

### Not done yet

- GIS map (the concept's second viewer): Forma holds no geolocation for assets. Issues have `gpsCoordinates`; could be a later option.
- Issue pushpins in the 3D view.
- Matching by Revit `UniqueId` (`Unique_ID` custom attribute, 2,902 assets) as a second key.

## Layout (version 1, kept for reference)


1. **Header:** project name, hub, data as of (date and time), signed-in user, stale banner if the last run failed.
2. **Summary tiles:** systems total, ready, not ready, unknown. Open issues and open forms linked to assets.
3. **Systems list (left):** one row per system with a status pill (ready / not ready / unknown), number of assets, number of blocking items. Sort: not ready first. Search box.
4. **Assets panel (middle):** when a system is clicked, its assets with status pill and blocker count.
5. **References panel (right):** when an asset is clicked, every linked issue, form and document, grouped by type, with status, assignee, due date, the path from the asset, and an "Open in Forma" link.

## Behaviour

- Filters: status, category, only blocking items.
- Everything is client-side; no API calls from the browser.
- Colour is not the only signal: pills also carry text.
- Follows Autodesk brand colours where practical (see `autodesk-brand-visual` skill).

## Later (not phase 1)

- Trend over time from daily snapshots.
- "Raise issue" button (phase 2, needs write scope).
- Export to Excel for handover meetings.
