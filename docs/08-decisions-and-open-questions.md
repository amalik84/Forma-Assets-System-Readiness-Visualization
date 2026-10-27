# 08. Decisions and open questions

## Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-10-21 | Phase 1 is read only | Agreed in kick-off call |
| 2026-10-21 | Runtime script uses no AI | Agreed in kick-off call: daily refresh without AI |
| 2026-10-21 | 3-legged OAuth with the existing custom integration | Data respects user permissions; integration already exists |
| 2026-10-21 | Python + static HTML, Windows Task Scheduler | Simplest path to a daily dashboard (proposed by Claude, confirm) |
| 2026-10-21 | Python standard library only, no pip packages | files.pythonhosted.org fails TLS on the corporate network (untrusted root). Autodesk APIs work fine with stdlib. |
| 2026-10-21 | Systems = asset custom attribute, set by `SYSTEM_ATTRIBUTE` in `.env` (default `System Classification`) | No public Systems API. Configurable so the real project can use its own attribute. |
| 2026-10-21 | Traversal: first hop shows all link types; walk only through issues, forms, documents; `MAX_DEPTH=2` | Agreed by the project owner (question 10). Depth 2 chosen after depth 3 pulled in every issue pinned on a shared Revit model. |
| 2026-10-21 | Live viewer through a local server (`serve.py`), token never in the HTML | Agreed by the project owner. Static file keeps working without the viewer. |
| 2026-10-21 | Viewer models: Arch_demo + MEP-central + Struc (most-linked copies that translate) | Agreed by the project owner (Arch + MEP); Struc added so B10 shows. Configurable via `VIEWER_MODELS`. |
| 2026-10-21 | Snapshots stored per project: `data/raw/<projectId>/YYYY-MM-DD/` | Switching project the same day mixed files. Demo project A snapshot moved under its project id. |
| 2026-10-21 | Active project switched to **Demo project B** (`<id>`, account `<id>`). Demo project A snapshot kept under its project id. | Set in `.env` |
| 2026-10-21 | Demo project B: systems = top-level asset category (`SYSTEM_ATTRIBUTE=category`), 7 systems covering all 688 assets | Agreed by the project owner. No System Classification attribute; Route / Line Name covered only 266 assets. |
| 2026-10-21 | Demo project B viewer models: MN_GC_0001.rvt (Tunnel 307 of 334) + RidgeGate_Station_SITE.dwg (Light Poles 29 of 29) | 20 referenced models tested in the viewer; only these two match asset names. |
| 2026-10-27 | Forma Systems through the Data Connector, lean: one daily request with only the `assets` service group for this project, download only the two system files; everything else stays on the live APIs | Assets API has no Systems endpoint (404); Data Connector exports systems and memberships with matching asset ids. Agreed by the project owner. |
| 2026-10-21 | Join on IDs from Relationships | Relationship entity IDs match Issues API IDs (18/18) and Forms API IDs (16/19) |
| 2026-10-21 | Hub and project set in .env | Hub `<id>`, project `<id>` (stored without `b.`) |

## Open questions

| # | Question | Owner | Needed by |
|---|---|---|---|
| 1 | ~~Which hub and project do we start with?~~ Answered 2026-10-21 | team | Step 2 |
| 2 | ~~Decided 2026-10-21: custom attribute, see decisions.~~ Still to check: which attribute the real customer project uses, and whether assets can belong to more than one system. Original note: **How do we group assets into systems?** No public Systems API (404). Relationships knows a `system` type but Demo project A has 0. Custom attribute `System Classification` (`ca29`) is filled on 258 of 6,516 assets (`B10` 257, `Supply Air` 1). Options: (a) a custom attribute, (b) asset category, (c) location, (d) a mapping file we maintain. Which project data will the real use case have? | team | Step 4 |
| 3 | Which issue statuses count as done? Is `completed` enough or only `closed`? | team | Step 7 |
| 4 | Which form statuses count as done? Seen: `draft`, `inReview`, `submitted`. Is `submitted` done? | team | Step 7 |
| 5 | ~~Should traversal pass through other assets?~~ Moot: Relationships cannot link asset to asset. The code stops at assets anyway. | | |
| 6 | Whose account does the daily run use? If that person is away 2+ weeks, the token expires. | team | Step 9 |
| 10 | ~~Decided 2026-10-21, see decisions.~~ **Which link types does the readiness traversal walk through?** Proposal: start at the asset, follow links to issues, forms and documents, and from those on to further issues and forms. Do not walk through meeting items, RFIs, schedule activities, photos or cost items (2,450 issue to meeting item links would pull in most of the project). Show those other links in the dashboard as references only. | team | Step 7 |
| 11 | Do the Open in Forma links for issues, forms and assets open the right item? Formats are best guesses in `.env` (`FORMA_ISSUE_URL`, `FORMA_FORM_URL`, `FORMA_ASSET_URL`). Document links come from the API and are fine. | owner | Step 9 |
| 12 | Is the lifecycle phase mapping in `src/lifecycle.py` right (which issue types and form types are design, execution, handover)? | team | before demo |
| 13 | Which model copies are the real ones? The project has up to 10 copies of each model; Forma assets do not say which model they came from. | team | before demo |
| 14 | **New project (2026-10-21): Demo project C** (`<id>`, account `<id>`). Assets 403 "User is not a project member or does not have access to the assets product"; Data Management 403; Issues and Forms answer but show 1 issue. Needed: the user added as project member with Build / Assets access, and Document Management access on the custom integration in this account. Also: which custom attribute holds the system here, and which models to show (`SYSTEM_ATTRIBUTE`, `VIEWER_MODELS`). | owner / project admin | refresh |
| 15 | Demo project B: HVAC units (37) and Structural (18) are in no linked model; Road (211) and Rail (55) assets have plain names ("Tangenziale Ovest di Milano", "SIG-CORK-COBH-0001") so name matching cannot place them. Road assets carry `IFCguid` (212): matching by IFC GUID against an IFC model would be the next step. | owner | viewer coverage |
| 7 | Where is the dashboard viewed: local file, SharePoint, a hosted page? | team | Step 9 |
| 8 | Rotate the client secret once setup works (it was shared in a chat). | team | Step 9 |
| 9 | ~~Partly solved 2026-10-21: document lookups (`items/{urn}`) work, hub and project listing still 403. Enough for the dashboard.~~ Original: Data Management returns 403 for user and app tokens. Is "Document Management" access ticked on the custom integration in Account Admin? Needed for document names and links. | owner / account admin | Step 6 |
