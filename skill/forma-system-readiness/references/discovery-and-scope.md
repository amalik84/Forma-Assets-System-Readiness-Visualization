# 01 · FOMO1 Project Brief

## Problem
Before a building system (HVAC, electrical, fire protection…) can launch or be handed over, every open issue that touches it must be resolved. Today those issues are scattered: some are linked straight to an asset, others are pinned on a drawing that's linked to the asset, others come from a commissioning form. People miss them, which is where the name comes from (Fear Of Missing Out).

## Goal
A **visual dashboard** that shows, per system, whether it is **ready to launch**. The dashboard is refreshed **every morning by a script that needs no AI**.

- Click a **system** to see its assets and how many are clear.
- Click an **asset** to see every **issue, form and document** linked to it, the **reference path** (e.g. `AHU-01 → AHU submittal Rev B.pdf → Issue #42`) and each item's status.

## Definitions
| Term | Meaning in FOMO1 |
|---|---|
| **Forma** | Autodesk Forma (formerly Autodesk Construction Cloud / Autodesk Build). |
| **Project** | One Forma project inside one hub (account). |
| **Asset** | A record in Forma Assets (equipment, device, component). |
| **System** | A group of assets. **There is no public Systems API**, so a system is derived from an asset custom attribute (default `System`) or from the asset category. See `readiness-rules.md`. |
| **Reference** | Any issue, form, document or other asset reachable from an asset through Relationships or issue pushpins, up to `MAX_DEPTH` hops. |
| **Blocking** | An issue whose status isn't closed (or a warning status), or a form that is still in progress / in review. |
| **Ready** | Asset: zero blocking references. System: all its assets are ready. |

## Scope
**Phase 1 (now) — read-only**
1. Authentication: APS custom integration, 3-legged OAuth, daily silent refresh.
2. APIs: Data Management (hubs, projects, documents), Assets, Relationships, Issues, Forms.
3. Visual dashboard: static HTML, refreshed daily by Windows Task Scheduler.

**Phase 2 (later) — write-back:** raise issues from dashboard findings, link them to assets. See `writeback-phase2.md`.

## Inputs already in place
- APS custom integration created and activated in Forma (Account Admin → Custom Integrations).
- Client ID, client secret, callback URL `http://localhost:8080/` → stored in local `.env` only.
- Base URL `https://developer.api.autodesk.com`.

## Open decisions (confirm with the customer)
1. **How are systems defined in the project?** Asset custom attribute (which name?) or category? Or assets linked to a "parent system" asset?
2. **Which issue statuses count as resolved?** Default: only `closed`. Is `completed` (work done, awaiting verification) acceptable for launch?
3. **Which forms block?** Default: any form in progress / in review linked to the asset. Restrict to commissioning templates?
4. **Asset status gate?** e.g. asset must be `Commissioned` to be ready (`READY_ASSET_STATUSES`).
5. **Who sees the dashboard?** It contains whatever the signed-in user can see. Decide where the HTML file is shared (SharePoint/Teams folder with restricted access).

## Success criteria
- Dashboard matches Forma for a sample of 10 assets (same open issues and forms).
- Daily job runs unattended for 2+ weeks without re-login.
- A field engineer can find why a system is not ready in under 1 minute.
