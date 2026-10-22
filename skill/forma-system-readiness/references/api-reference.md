# 04 · Forma (ACC) API Reference for FOMO1

Base URL: `https://developer.api.autodesk.com`. All calls send `Authorization: Bearer <3-legged token>`. Scope: `data:read` covers every endpoint below.
Verified against the APS OpenAPI specs and the APS docs (October 2026). Items marked **UNVERIFIED** should be tested with `python fomo1.py check` first.

## ID rules (most common bug)
| API family | Project ID format |
|---|---|
| Data Management (`/project/v1`, `/data/v1`) | `b.<uuid>` (hub too: `b.<account uuid>`) |
| Issues, Forms, Relationships (`containerId`) | bare `<uuid>`, without `b.` |
| Assets | either form (FOMO1 uses bare) |

## Pagination styles
| Style | Used by | How to page |
|---|---|---|
| JSON:API | Data Management | `page[number]`, `page[limit]` (≤200); follow `links.next.href` |
| Offset | Issues, Forms, Categories | `limit`, `offset`; stop at `pagination.totalResults` |
| Cursor | Assets v2, asset statuses, custom attributes | `limit` (≤200) + `cursorState`; stop when `pagination.cursorState` is absent (or follow `pagination.nextUrl`) |
| Continuation | Relationships | `pageLimit` (≤100) + `continuationToken` from `page.continuationToken` |

`aps_client.iter_items()` handles nextUrl, cursor and offset automatically.

## 1. Data Management
| Purpose | Request |
|---|---|
| List hubs | `GET /project/v1/hubs` |
| List projects | `GET /project/v1/hubs/{hubId}/projects` |
| Get project | `GET /project/v1/hubs/{hubId}/projects/{b.projectId}` → `data.attributes.name` |
| Top folders | `GET /project/v1/hubs/{hubId}/projects/{b.projectId}/topFolders` |
| Folder contents | `GET /data/v1/projects/{b.projectId}/folders/{folderId}/contents` |
| Get item (document) | `GET /data/v1/projects/{b.projectId}/items/{urlencoded lineage URN}` → `data.attributes.displayName` |
| Item versions | `GET /data/v1/projects/{b.projectId}/items/{itemId}/versions` |

URNs: lineage `urn:adsk.wipprod:dm.lineage:ABC`; version `urn:adsk.wipprod:fs.file:vf.ABC?version=3`. FOMO1 normalises versions to lineage.

## 2. User
| Purpose | Request |
|---|---|
| Who am I | `GET https://api.aps.autodesk.com/userinfo` (legacy host `developer.api.autodesk.com/userinfo` still works). Fields: `name`, `email`, `sub` |
| Issues permissions in project | `GET /construction/issues/v1/projects/{pid}/users/me` → `isProjectAdmin`, `issues.permittedActions`, `permissionLevels` |

## 3. Issues v1 — `/construction/issues/v1/projects/{pid}`
| Purpose | Request |
|---|---|
| List issues | `GET /issues?limit=100&offset=0` |
| Useful filters | `filter[status]=open,pending`, `filter[linkedDocumentUrn]=<urn>`, `filter[issueTypeId]`, `filter[assignedTo]`, `filter[updatedAt]=2026-10-01..`, `filter[deleted]=false`, `filter[search]` |
| One issue | `GET /issues/{issueId}` · comments `GET /issues/{issueId}/comments` |
| Types | `GET /issue-types?include=subtypes` |
| Custom attributes | `GET /issue-attribute-definitions` |
| Root causes | `GET /issue-root-cause-categories?include=rootcauses` (include value UNVERIFIED) |

**Statuses**: `draft`, `open`, `pending`, `in_progress`, `in_review`, `completed`, `not_approved`, `in_dispute`, `closed`.
Key fields: `id`, `displayId`, `title`, `status`, `dueDate`, `assignedTo`, `assignedToType`, `issueTypeId`, `issueSubtypeId`, `linkedDocuments[]` (pushpins: `type`, `urn`, `createdAtVersion`, `details`), `deletedAt`.
Optional header `x-ads-region: US | EMEA | AUS …`.

## 4. Assets — `/construction/assets`
| Purpose | Request |
|---|---|
| List assets | `GET /v2/projects/{pid}/assets?limit=200&includeCustomAttributes=true` (cursor) |
| Filters | `filter[categoryId]`, `filter[statusId]`, `filter[locationId]` + `includeSubLocations`, `filter[customAttributes][<name>]`, `filter[searchText]`, `filter[updatedAt]`, `includeDeleted` |
| Batch get | `POST /v2/projects/{pid}/assets:batch-get` body `{"ids":[…]}` |
| Categories | `GET /v1/projects/{pid}/categories` (tree; `subcategoryIds`, `filter[parentId]`, `filter[maxDepth]`) |
| Statuses | `GET /v1/projects/{pid}/asset-statuses`, `GET /v1/projects/{pid}/status-step-sets` |
| Custom attributes | `GET /v1/projects/{pid}/custom-attributes` → `name` (key used in `asset.customAttributes`, e.g. `ca1`) + `displayName` (e.g. `System`) |

Asset fields: `id`, `clientAssetId` (the visible asset ID/name), `description`, `categoryId`, `statusId`, `locationId`, `customAttributes{}`, `isActive`, `deletedAt`.

**Systems:** earlier research found no documented public Systems endpoint (searches in October 2026 also found none), but Forma does have systems in the UI. Do not guess: run `python fomo1.py probe`. It prints one full asset record (a system reference may be a top-level field) and tests candidate endpoints with the user's own token. Then set `SYSTEM_GROUP_BY=asset_field` + `SYSTEM_FIELD_NAME` (+ `SYSTEMS_ENDPOINT` to turn IDs into names).

## 5. Relationships v2 — `/bim360/relationship/v2/containers/{pid}`
| Purpose | Request |
|---|---|
| Search | `GET /relationships:search?domain=&type=&id=&withDomain=&withType=&withId=&pageLimit=100&continuationToken=` |
| Intersect | `POST /relationships:intersect` body `{entities:[…], withEntities:[…]}` (1–30 each) |
| Batch get | `POST /relationships:batch` |
| Sync (incremental) | `POST /relationships:sync` body `{syncToken}` or `{filters}` → `current`, `deleted`, `moreData` |
| Writable domains | `GET /bim360/relationship/v2/utility/relationships:writable` (use it to discover the Forms domain) |

Response: `{page:{continuationToken, syncToken}, relationships:[{id, isDeleted, entities:[{domain,type,id},{domain,type,id}]}]}`.

| Domain | Types |
|---|---|
| `autodesk-bim360-asset` | `asset`, `system`, `category`, `categoryuid`, `systemcategory` (verified via `relationships:writable`) |
| `autodesk-bim360-issue` | `issue`, `quality`, `design`, `collaboration`, `coordination` |
| `autodesk-bim360-documentmanagement` | `documentlineage`, `documentversion`, `filelineage`, `fileversion` |
| `autodesk-bim360-checklist` | `checklist`, `checklisttemplate` |
| `autodesk-bim360-rfi` | `rfi` |
| `autodesk-construction-form` | `form`, `formfield`, `formtemplate` (verified on two projects; FOMO1 classifies any domain containing `form` as a form) |

Other domains seen in real projects (ignored by FOMO1 because they are not assets, issues, forms or documents): `autodesk-bim360-meetingminutes/meetingitem`, `autodesk-construction-schedule/activity|task`, `autodesk-construction-markup/*`, `autodesk-construction-photo/photo`, `autodesk-bim360-modelcoordination/*`, `autodesk-bim360-cost/pco|rfq`, `autodesk-construction-submittals/submittalitem`, `autodesk-construction-correspondence/thread`.

Domain-wide search (no `id`) is used for speed. If it's refused, FOMO1 searches per asset (slower: 120 req/min).

## 6. Forms — `/construction/forms`
| Purpose | Request |
|---|---|
| List forms (v2, **beta**, preferred) | `GET /v2/projects/{pid}/forms?limit=200&offset=0` (+ `statuses`, `templateId`, `updatedAfter`, `locationIds`, `sort`) → `{data[], pagination{offset,limit,totalResults,nextUrl}}` |
| List forms (v1, deprecated) | `GET /v1/projects/{pid}/forms` (`sortBy`, `sortOrder`) |
| Templates | `GET /v1/projects/{pid}/form-templates` |

Status mapping: v1 `draft` → v2 `inProgress`; `in_review` → `inReview`; `submitted` → `closed`; `discarded`, `archived` unchanged.

## 7. Rate limits (per minute)
Issues 500 per user/hub · Assets reads 1000 / writes 100 / asset-relationships 50 · Relationships 120 per user · Forms 100 per app · Token endpoint 500. HTTP 429 → wait for `Retry-After` and retry. `aps_client.py` throttles and retries automatically.

## Verified on real projects (October 2026)

Called successfully on Demo project A and Demo project B with a 3-legged `data:read` token:

| Finding | Detail |
|---|---|
| Relationships paging | Max 100 per page whatever `pageLimit` says. 7,848 relationships = 79 pages, about 40 s |
| Relationship ids match | Issue ids in Relationships match the Issues API (18 of 18); form ids match the Forms API (16 of 19, the rest deleted or no access) |
| Document ids | Three forms: `urn:...:dm.lineage:X`, `...X#3D View` (a view), `...X?version=1` (type `documentversion`). Strip `#...` and `?...` and call `items/{urn}` |
| Issue pins | `issue.linkedDocuments[].urn` is a lineage URN. On Demo project A none of the 224 pins were also in Relationships, so pins are a real extra edge source |
| Systems | No endpoint: `assets v1/v2 systems`, `asset-systems`, `systems v1`, `assets v3 systems`, `system-categories`, `systems:search` all 404 |
| Asset lifecycle | `asset-statuses` carry `statusStepSetId` + `sortOrder`; `status-step-sets` give the set name. Together they give each asset's step, e.g. Doors: Specified > Planned > Ordered > Delivered > Installed > Checked |
| Viewer models | `GET /data/v1/projects/{b.pid}/items/{urn}/tip` gives the latest version and its derivative URN; `GET /modelderivative/v2/designdata/{urn}/manifest` gives `status` (`success` / `failed`). `data:read` is enough for the APS Viewer |
| Project name and account | `GET /construction/admin/v1/projects/{pid}` works with an app-only `account:read` token (3-legged `data:read` gets 403). Used only to find the right account id |
| Open in Forma for documents | `items/{urn}` → `data.links.webView.href` |

## Sources
APS OpenAPI specs (github.com/autodesk-platform-services/aps-sdk-openapi) · aps.autodesk.com/en/docs/acc/v1 (Assets v2, Relationships search & tutorial, Forms v2 and v1→v2 migration guide, rate limits) · APS OAuth v2 field guide · APS blog "Get to know the new Autodesk Forma industry cloud" (Mar 2026).
