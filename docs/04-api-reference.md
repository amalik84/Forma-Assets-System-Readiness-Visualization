# 04. API reference (phase 1, read only)

Base URL: `AUTODESK_FORMA_API_BASE_URL` = `https://developer.api.autodesk.com`

Official docs: https://aps.autodesk.com/developer/documentation (look under Data Management and Autodesk Construction Cloud APIs).

**Status column:** `verified` = called successfully against Demo project A on 2026-10-21. `known` = documented, not yet called. `404` = does not exist. `VERIFY` = check the current docs and a real response before building on it, then change it to `known` here.

## ID formats (common trap)

- Data Management uses hub and project IDs **with** the `b.` prefix: `b.1a2b3c...`
- Construction APIs (Assets, Issues, Forms, Relationships) use the project ID **without** `b.`: `1a2b3c...`
- Relationships uses the project ID (no `b.`) as `containerId` (verified 2026-10-21).

Store `FORMA_PROJECT_ID` without the prefix and add `b.` in the Data Management module.

## Access test results (2026-10-21, 3-legged, project Demo project A)

| API | Result |
|---|---|
| Assets `categories` | OK |
| Issues `users/me` | OK |
| Forms `form-templates` | OK |
| Relationships `relationships:search` | OK |
| Data Management `hubs`, `projects/b.{id}` | 403 `BIM360DM_ERROR` (still, later on 2026-10-21) |
| Data Management `items/{urn}` | OK after the integration change (181 of 181 documents) |
| ACC Admin `projects/{id}` | 403 with `data:read` only; needs `account:read` scope. OK with an app-only token. |
| Legacy HQ v1 `accounts/{id}/projects` | 403 "client id has no access to the account" (legacy BIM 360 API, not needed) |

## 1. Data Management (who / which hub / which project / documents)

| Purpose | Method and path | Status |
|---|---|---|
| List hubs I can access | `GET /project/v1/hubs` | known |
| List projects in a hub | `GET /project/v1/hubs/{hubId}/projects` | known |
| Top folders | `GET /project/v1/hubs/{hubId}/projects/{projectId}/topFolders` | known |
| Folder contents | `GET /data/v1/projects/{projectId}/folders/{folderId}/contents` | known |
| Document (item) details | `GET /data/v1/projects/{projectId}/items/{itemId}` (itemId = URL-encoded lineage URN) | verified 2026-10-21: works after the integration change. `attributes.displayName`, `links.webView.href` (Open in Forma link). |
| Document versions | `GET /data/v1/projects/{projectId}/items/{itemId}/versions` | known |

Paging: JSON:API style, follow `links.next.href` until absent.

## 2. Assets

| Purpose | Method and path | Status |
|---|---|---|
| List assets | `GET /construction/assets/v2/projects/{projectId}/assets` | verified. `includeCustomAttributes=true` adds `customAttributes` (`ca1`, `ca2`...). Max `limit` 200. |
| List assets (v1) | `GET /construction/assets/v1/projects/{projectId}/assets` | verified, same shape. Use v2. |
| Categories | `GET /construction/assets/v1/projects/{projectId}/categories` | verified. Tree: `isRoot`, `isLeaf`, `subcategoryIds`. One root named `ROOT`. |
| Asset statuses | `GET /construction/assets/v1/projects/{projectId}/asset-statuses` | verified |
| Status sets | `GET /construction/assets/v1/projects/{projectId}/status-step-sets` | verified |
| Custom attributes | `GET /construction/assets/v1/projects/{projectId}/custom-attributes` | verified. Map `name` (`ca29`) to `displayName`. |
| Systems | `GET .../v1/.../systems`, `.../v2/.../systems` and 6 other guesses | **404**. No public Systems endpoint found in docs or by probing. See open question 2. |

Asset fields: `id`, `clientAssetId` (display name), `categoryId`, `statusId`, `locationId`, `barcode`, `isActive`, `customAttributes`, timestamps.

Paging: `pagination.nextUrl` (and `cursorState`). `aps_client.get_all_cursor()` handles it. Demo project A: 6,516 assets.

## 3. Relationships

| Purpose | Method and path | Status |
|---|---|---|
| Search | `GET /bim360/relationship/v2/containers/{projectId}/relationships:search` with `domain`, `type`, `id`, `withDomain`, `withType`, `pageLimit` (200) | verified |
| Allowed link types | `GET /bim360/relationship/v2/utility/relationships:writable` | verified |
| Bulk sync | `POST /bim360/relationship/v2/containers/{projectId}/relationships:sync` | known, not yet called |

Response: `relationships[]` (each has `id`, `isDeleted`, `createdOn`, `entities[2]` with `domain`, `type`, `id`) and `page` with `continuationToken` and `syncToken`. Paging verified: pass `continuationToken` as a query parameter. Max 100 per page whatever `pageLimit` says. Demo project A: 7,848 relationships, 79 pages, about 40 s.

Document ids come in three forms: `urn:adsk.wipprod:dm.lineage:XYZ`, `...XYZ#3D View` (a view inside the document) and `...XYZ?version=1` (type `documentversion`). Strip `#...` and `?...` before calling Data Management.

| Entity | domain | type | Confirmed |
|---|---|---|---|
| Asset | `autodesk-bim360-asset` | `asset` | yes |
| System | `autodesk-bim360-asset` | `system` | yes, but 0 relationships in Demo project A |
| Issue | `autodesk-bim360-issue` | `issue` | yes. IDs match Issues API (18 of 18). |
| Form | `autodesk-construction-form` | `form` | yes. IDs match Forms API (16 of 19; 3 not returned, probably deleted or no access). |
| Document | `autodesk-bim360-documentmanagement` | `documentlineage` (also `documentversion`) | yes. Names need Data Management (403 for now). |

Assets link to: issues, forms, documents, photos, sheets, submittals, schedule activities and tasks, RFIs, meeting items, cost items, correspondence, reviews, packages, specifications. Assets **cannot** be linked to other assets or to systems through Relationships (per `relationships:writable`).

Issues and forms can also link to each other and to documents, so multi-level chains (asset > form > issue) are possible.

## 4. Issues

| Purpose | Method and path | Status |
|---|---|---|
| List issues | `GET /construction/issues/v1/projects/{projectId}/issues` | verified. `limit` up to 100, `offset`. `pagination.totalResults`. |
| One issue | `GET /construction/issues/v1/projects/{projectId}/issues/{issueId}` | known |
| Issue types | `GET /construction/issues/v1/projects/{projectId}/issue-types?include=subtypes` | verified (17). 25 issues point to a type not in this list (probably deleted/inactive), shown with an empty type. |
| Attribute definitions | `GET /construction/issues/v1/projects/{projectId}/issue-attribute-definitions` | verified (10) |
| My permissions | `GET /construction/issues/v1/projects/{projectId}/users/me` | verified |

Demo project A: 332 issues. Statuses seen: `open` 249, `pending` 37, `in_review` 28, `closed` 15, `draft` 3.

## 5. Forms

| Purpose | Method and path | Status |
|---|---|---|
| List forms | `GET /construction/forms/v1/projects/{projectId}/forms` | verified. Results in `data`, paging via `pagination.nextUrl`. `limit` 50. |
| Form templates | `GET /construction/forms/v1/projects/{projectId}/form-templates` | verified (31) |

Demo project A: 147 forms (same with `includeInactiveFormTemplates=true`). Statuses seen: `draft` 85, `submitted` 58, `inReview` 4.

Form fields: `id`, `formNum`, `name`, `status`, `formTemplate`, `assigneeId`, `dueDate`, `formDate`, `locationId`, `customValues`, `tabularValues`, `lastSubmitterSignature`.

## 6. Rate limits and errors

- `429`: wait for `Retry-After` seconds, retry up to 5 times with backoff (in `aps_client.request`).
- `401`: refresh token once, retry once, then fail.
- `403`: the user lacks access to that module. Mark the area `unknown`, continue.
- Log the endpoint and status code, never the token.
