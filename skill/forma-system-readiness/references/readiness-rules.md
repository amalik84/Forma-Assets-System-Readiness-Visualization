# 05 · Readiness Rules & Traversal

## 1. Grouping assets into systems
There's no public Systems API, so `SYSTEM_GROUP_BY` decides:

| Mode | Rule | When to use |
|---|---|---|
| `custom_attribute` (default) | Value of the asset custom attribute whose **display name** = `SYSTEM_ATTRIBUTE_NAME` (default `System`). Its internal key (e.g. `ca3`) is looked up from `/custom-attributes`. | The project has a "System" field on assets (most common in commissioning). |
| `category` | Asset category name. | Categories are organised by system (HVAC, Electrical…). |
| `map_file` | `system_map.csv` next to `fomo1.py`: one row per asset with a **System** column and an identifier column (`Asset ID` = the asset's visible name, `Name`, `Id`, or `Barcode`). Comma, semicolon or tab separated. Unmatched assets show as `(Not in system map)`. | The project has Forma systems but the API does not expose them (the first project: probe found no system field and all candidate endpoints returned 404). Export from Forma or build the CSV, then `python fomo1.py regroup --open`. |
| `asset_field` | A top-level field of the asset record (`SYSTEM_FIELD_NAME`, dots allowed), optionally resolved to names via `SYSTEMS_ENDPOINT`. | Forma returns the asset's system as a field; find it with `python fomo1.py probe`. |

Assets with no value go to `(No system set)`. This group is a data-quality to-do list.
Future option: a "parent system" asset with child assets linked through Relationships.

### Same choices in the live build (`Documents\code\forma-system-readiness`)

The live build has one setting, `SYSTEM_ATTRIBUTE`: a custom attribute display name (FOMO1 `custom_attribute`), or `category` for the **top-level** category (`Tunnel > Galleria` goes to `Tunnel`). Map files and asset fields are FOMO1 only; port them if a project needs them.

## 2. The reference graph
Nodes: `asset`, `issue`, `form`, `document`, `rfi`. Edges come from two sources:
1. **Relationships API**: every non-deleted relationship whose two entities are both recognised kinds.
2. **Issue pushpins**: `issue.linkedDocuments[].urn` → document node (normalised to the lineage URN).

Domain → kind: `*asset*` + type `asset` → asset · `*issue*` → issue · `*form*` / `*checklist*` → form · `*documentmanagement*` → document · `*rfi*` → rfi · everything else is ignored.

## 3. Walking from an asset (breadth-first, shortest path kept)
- Start at the asset. Follow edges up to `MAX_DEPTH` hops (default 3).
- **Pass-through nodes** (keep walking): `document`, `form`.
- **Assets**: walked only through asset→asset chains (child equipment), and only when `FOLLOW_ASSET_LINKS=true`. Assets that share a document with this one are *not* walked, so their issues aren't attributed here.
- **Leaves** (stop): `issue`, `rfi`.
- Each reference stores its **path**, e.g. `AHU-01 → AHU submittal Rev B.pdf → Issue #42 Insulation damaged`.

Examples it catches:
```
asset → issue                               (direct link)
asset → document → issue                    (issue pinned on a linked drawing)
asset → form → issue                        (issue raised from a commissioning form)
asset → child asset → issue                 (component of the equipment)
asset → form → document → issue             (depth 3)
```

### Live build differences (learned on Demo project A)

- `MAX_DEPTH=2` by default. Depth 3 pulled every issue pinned on a shared Revit model into each linked asset (door W107: 13 to 80 blockers).
- At the first hop every link type is kept as a reference (meeting items, RFIs, schedule activities, photos, cost items) and shown, but only issues, forms and documents are walked through and only issues and forms block.
- Each reference also gets a lifecycle **phase** (Design / Execution / Handover and operations) from its type, in `src/lifecycle.py`. Forma has no phase field.

## 4. State of each reference
| Kind | blocking | warning | ok |
|---|---|---|---|
| Issue | status ∉ `ISSUE_CLOSED_STATUSES` ∪ `ISSUE_WARNING_STATUSES` | status ∈ `ISSUE_WARNING_STATUSES` (default `draft`) | status ∈ `ISSUE_CLOSED_STATUSES` (default `closed`) |
| Form | status ∈ `FORM_OPEN_STATUSES` (default `inProgress,inReview,draft,in_review`) | – | otherwise |
| Not visible (in a relationship, but not returned to this user) | – | ✓ (shown as "no access") | – |
| Asset status rule | asset status label ∉ `READY_ASSET_STATUSES` (only if that is set) | – | – |
| Document / RFI / linked asset | – | – | shown for context |

## 5. Roll-up
- **Asset ready** = 0 blocking references.
- **System ready** = every asset in it is ready. Progress = ready assets ÷ assets.
- Project KPIs: systems ready, assets clear, unique blocking issues, unique blocking forms, and **open issues not linked to any asset** (a hint that linking is incomplete in Forma).

## 6. Tuning without code
All rules live in `.env`: `SYSTEM_GROUP_BY`, `SYSTEM_ATTRIBUTE_NAME`, `ISSUE_CLOSED_STATUSES`, `ISSUE_WARNING_STATUSES`, `FORM_OPEN_STATUSES`, `READY_ASSET_STATUSES`, `MAX_DEPTH`, `FOLLOW_ASSET_LINKS`, `REL_DOMAINS`.
Example for a stricter handover: `ISSUE_CLOSED_STATUSES=closed`, `READY_ASSET_STATUSES=Commissioned`.
Example for a looser view: `ISSUE_CLOSED_STATUSES=closed,completed`.

## 7. System dependencies (launch topology)
Forma has no "system feeds system" data, so dependencies are a small config file, `app/systems.json`:
```json
{ "placeholder": false, "feeds": [["Electrical", "HVAC"], ["HVAC", "Vertical Transport"]] }
```
Each pair is `[upstream, downstream]`: the downstream system cannot launch before the upstream is ready. Names must match the dashboard's system names exactly; unmatched pairs are listed in the dashboard, not drawn. `"placeholder": true` shows a "starter dependencies" banner.

Derived values per system (computed in `dashboard-ui/src/lib/model.ts`):
- **up / down**: transitive upstream and downstream systems.
- **fed by blocked**: an upstream system is NO-GO, so this system cannot launch either (warning on the node and in details).
- **roll-up badge (▼N)**: distinct blocking items anywhere downstream, so a problem on a downstream system flags every system above it.
- Systems in no pair appear under "Independent systems".

Edit `systems.json`, then `python fomo1.py render --open` (no Forma calls needed).
