# 07 · Phase 2 Roadmap: Write-back (NOT in scope yet)

Phase 1 must be stable first (2+ weeks of clean daily runs, numbers validated against Forma).

## Candidate features
1. **Raise an issue from the dashboard**: e.g. "Asset has no commissioning form" or "System X blocked by overdue items".
   - `POST /construction/issues/v1/projects/{pid}/issues` (title, issueSubtypeId, status, assignedTo, dueDate…)
   - Check `GET /issues/v1/projects/{pid}/users/me` → `issues.permittedActions` includes create.
2. **Link the new issue to the asset**: Relationships `PUT /bim360/relationship/v2/containers/{pid}/relationships` with the entities `{autodesk-bim360-asset, asset, id}` and `{autodesk-bim360-issue, issue, id}` (the create endpoint is UNVERIFIED; also confirm the domain is writable via `relationships:writable`).
3. **Update the asset status** when a system becomes ready (Assets write: 100 req/min).
4. **Incremental refresh** via `relationships:sync` + `filter[updatedAt]` to cut run time.
5. **Secure Service Account** for server-side unattended runs.

## Required changes
- Scope `data:write` (and `data:create`) added to `APS_SCOPES`, then re-login.
- Writes must go through a confirmation step, run as a named user and be logged to `output/logs/writes.log`.
- A static HTML file can't call APIs securely, so write-back needs a small local service or a human-in-the-loop step (e.g. the dashboard exports a "proposed issues" CSV → `python fomo1.py raise --file proposals.csv`).
