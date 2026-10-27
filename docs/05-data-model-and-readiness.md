# 05. Data model and readiness rules

## Entities (normalised, what we store in `data.json`)

```
System     { id, name, assetIds[], isUnassigned }
Asset      { id, name, barcode, category, status, statusColor, locationId, systemIds[] }
Issue      { id, displayId, title, status, isDone, type, subtype, assignedTo, assignedToType, dueDate, locationId, published, linkedDocumentUrns[], updatedAt }
Form       { id, formNum, name, template, templateType, status, isDone, assigneeId, assigneeType, dueDate, formDate, locationId, updatedAt }
Document   { id, name, folderPath, version, url }
Edge       { from: {type, id}, to: {type, id}, source: "relationships" | "issue.linkedDocuments" | ... }
```

## Systems

There is no public Systems API (docs/04). Assets are grouped by the custom attribute named in `SYSTEM_ATTRIBUTE` (`.env`, default `System Classification`).

- The display name is resolved to its key (`ca29`) at run time, so renaming works per project.
- `SYSTEM_ATTRIBUTE=category` groups by the top-level asset category instead (`Tunnel > Galleria` goes to `Tunnel`). Used for Demo project B.
- `SYSTEM_ATTRIBUTE=dataconnector` uses the real Forma Systems (Assets > Systems). The Assets API has no Systems endpoint and Relationships holds almost no system links, but the Data Connector `assets` service group exports `assets_systems.csv` (id, name, status_id, category_uid, deleted_at) and `assets_system_memberships.csv` (system_id, member_type `asset` or `system`, member_id). Member ids equal Assets API ids (314 of 314 on the first project). `src/fetch/systems_dc.py` keeps one recurring daily request (assets only, this project), downloads only those two files from the newest successful job, and saves `systems.json`. Systems inside systems become a path ("Parent > Child"). Each system also gets its Forma system category (`category_uid` resolved through `assets_categories.csv` `uid`; nested systems inherit their parent's), shown as group headers in the dashboard and as "System category" in Power BI. Three small files are downloaded per extract.
- System id = the trimmed attribute value. One system per asset for now.
- Assets with an empty value go to the `(no system)` bucket, shown last. Their readiness is **unknown**.
- Inactive assets are skipped.
- Category is shown as a path without the technical `ROOT` node, for example `Ducts > Rectangular Duct`.

Implemented in `src/fetch/assets.py`, tested in `tests/test_assets.py`.

## Reference graph

- Nodes: assets, issues, forms, documents.
- Edges: every relationship returned by the Relationships API, treated as **undirected**.
- Extra edges from issue `linkedDocuments[].urn` (issue pinned on a document, lineage URN): 224 in Demo project A, **none of them also in Relationships**, so they are a real extra source. Saved as `pinEdges` in `documents.json` with `source: issue.linkedDocuments`.
- Node key everywhere: `type:id`, for example `issue:4f2a...`, `documentlineage:urn:adsk...`. Edges: `{id, a, aDomain, b, bDomain, createdOn, source}`.
- All relationship types are saved (meeting items, RFIs, schedule activities, cost items...). In Demo project A assets link most to schedule activities (771) and tasks (94); to forms 77, issues 26, documents 11. Which types the traversal walks through is decided in step 7 (open question 10).
- Deleted issues are skipped. `isDone` is set at fetch time from `ISSUE_DONE_STATUSES` / `FORM_DONE_STATUSES` (comma-separated, case-insensitive).
- Names of assignees are not resolved yet (ids only). That needs the ACC Admin users API with `account:read` scope, decide in step 8.

### Multi-level traversal (implemented in `src/model.py`, decided 2026-10-21)

For each asset, a breadth-first search from that asset:

- **First hop:** every directly linked item is a reference, whatever its type (meeting items, RFIs, schedule activities, photos, cost items...). Shown in the dashboard, never blocking.
- **Walk on** only through issues, forms and documents, and beyond the first hop only record issues, forms and documents. So `asset > meeting item > issue` is **not** followed (2,450 issue to meeting item links would pull in most of the project).
- **Never walk through** another asset or a system.
- **Stop at `MAX_DEPTH`, default 2.** Depth 3 was tried on Demo project A: asset W107 went from 13 to 80 blockers, 67 of them via one Revit model (`asset > form > LTU Housing - Arch_demo.rvt > every issue pinned on the model`). Depth 2 keeps `asset > document > issue` and `asset > form > issue`, which is what the kick-off call described.
- A visited set handles loops. Each item appears once, with its **shortest** path, so the dashboard can show why it is linked: `Form #112 > Issue #130`.

## Readiness rules *(proposed, to confirm with the team)*

An item is **blocking** when:

| Item | Blocking when status is |
|---|---|
| Issue | anything except `closed`. Seen in Demo project A: `open`, `pending`, `in_review`, `draft`, `closed`. (`completed` not used here, decide if other projects use it.) |
| Form | anything except `submitted`? Seen: `draft`, `inReview`, `submitted`. To confirm. |
| Unresolved reference | a relationship points to an issue or form the API does not return (deleted or no access): show as **unknown**, never ignore silently |
| Document | never blocking by itself, only as a link to issues and forms |

Readiness:

- **Asset ready**: no blocking item reachable within `MAX_DEPTH`.
- **System ready**: all its assets are ready.
- **Unknown**: a linked issue or form was not returned by the API (deleted or no access). Never show ready when data is missing.
- Assets without a system are assessed too, but their bucket `(no system)` gets status **unassigned**, never ready.
- **Ready with nothing linked:** a system is ready if no asset has a blocking item, including when nothing is linked at all. `assetsWithReferences` is saved per system so the dashboard can say "0 of 257 assets have any links" (B10 in Demo project A).
- System `blockingCount` counts distinct items: one issue linked to five assets counts once.

Each not-ready result carries a list of reasons (blocking item + path).

## Settings (`.env`)

- `MAX_DEPTH=2`
- `ISSUE_DONE_STATUSES=closed`
- `FORM_DONE_STATUSES=submitted` (proposed, confirm)
