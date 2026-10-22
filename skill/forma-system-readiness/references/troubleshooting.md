# Troubleshooting and lessons from real projects

Collected on two real Forma projects: Demo project A (6,516 assets, 332 issues, 147 forms, 7,848 relationships) and Demo project B (688 assets, 76 issues, 19 forms, 647 relationships). Read this before guessing.

## Network, install and PowerShell

| Symptom | Cause | Fix |
|---|---|---|
| `pip install` fails with `SSLCertVerificationError` / untrusted root on `files.pythonhosted.org` | Company proxy re-signs HTTPS | **No install needed.** Both builds use only the Python standard library. Python on Windows uses the OS certificate store, which already trusts the company certificate for the Autodesk APIs |
| `python` says "Python was not found; run without arguments to install from the Microsoft Store" | Only the Store alias exists | Use `py` (the Python launcher). `schedule_daily.ps1` already prefers `py` |
| `login` works in the browser but the script can't reach `developer.api.autodesk.com` | Firewall blocks the host | Ask IT to allow `developer.api.autodesk.com` (and `api.aps.autodesk.com`), or use an allowed network |
| `npm install` fails | npm registry blocked | The React dashboard is optional: `render` uses the plain-HTML fallback until `dashboard-ui/dist/index.html` exists |
| `No such file: fomo1.py` | PowerShell is in the wrong folder | `cd` into the app folder first |
| "running scripts is disabled on this system" | Execution policy | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` (this window only) |
| Red `NativeCommandError` although the step worked | Windows PowerShell 5.1 turns Python stderr (warnings, retries) into error records | Judge by `$LASTEXITCODE`. `refresh.ps1` already does |
| Refresh stopped at documents: "relationships.json not found" | Run crossed midnight, steps used different dates | Fixed: `refresh.ps1` sets `SNAPSHOT_DAY` once. For manual runs set `$env:SNAPSHOT_DAY` first |

## Access and API behaviour

| Symptom | Meaning / fix |
|---|---|
| `Hubs (0)` with 403 "You don't have permission to access this API" in every region, also with an app-only token | The client ID is not active under Account Admin > Custom Integrations for that account, or the APS app lacks API access. Account admin fixes it |
| Assets 403 "User is not a project member or does not have access to the assets product" | Project admin adds the user with Build / Assets access |
| Data Management 403 on `hubs/.../projects/...` (`BIM360DM_ERROR`) while Issues, Assets, Forms, Relationships are OK | Partial Document Management access. **Harmless** if `items/{urn}` lookups work: document names and Open in Forma links still resolve. FOMO1 falls back to IDs for the project name |
| Data Management 403 everywhere | Wrong hub ID (project is in another account) or no Document Management access in that account. Look up the project's `accountId` and use it as the hub ID |
| ACC Admin `projects/{id}` 403 "Token does not have the privilege" | 3-legged token has only `data:read`; needs `account:read`. Not needed for the dashboard |
| Data Management 400 "Urn is not in the proper format" | The document id carries a view (`...#3D View`) or version (`...?version=1`). Strip `#...` and `?...` before calling `items/{urn}` |
| Forms v2 returns 400 | v2 is beta / not enabled; FOMO1 falls back to v1. The live build uses v1 |
| Empty issues in EMEA / AUS projects | Set `FORMA_REGION` (FOMO1 sends `x-ads-region`) |
| 404 on a project | Wrong ID format: Data Management needs `b.<uuid>`, the construction APIs the bare `<uuid>` |
| Systems endpoints all 404 | There is no public Systems API (8 paths probed on Demo project A). Derive systems: custom attribute, category, map file, or asset field. See `readiness-rules.md` |
| `SYSTEM_ATTRIBUTE '...' not found. Available: [...]` | New project, other custom attributes. Choose a new grouping with the user |
| Run takes minutes | Normal. 6.5k assets about 4 minutes. Relationships: max 100 per page, 120 requests per minute per user |
| `Re-login needed` / refresh token expired | No run for 15 days or token revoked: log in again (the user signs in in their browser) |
| `redirect_uri mismatch` or login page does nothing | Callback URL differs from the APS app setting (trailing slash, `localhost` vs `127.0.0.1`), or port 8080 is busy |

## Live viewer (live build only)

| Symptom | Fix |
|---|---|
| Viewer says "needs your login" | Page opened as a file. Use `.\serve.ps1` |
| "No token for the viewer" | Log in again, restart `serve.ps1` |
| Model shows `failed` in `models.py` | Translation failed in Forma (three Struc_demo copies did). Use another copy |
| Asset "not in the loaded models" | Name does not match an element, or its model is not in `VIEWER_MODELS`. See `model-matching.md` |

## Data surprises (check on every new project)

1. **Find the real systems first.** Demo project A: the best custom field (System Classification) was filled on 258 of 6,516 assets (4%). Demo project B had no system field at all; top-level category gave 7 systems covering all 688 assets. Category is a stopgap: agree the real definition with the customer.
2. **Most issues may not be linked to assets.** Demo project A: 289 of 332 issues were linked only to meeting items, schedule activities, markups, photos or model coordination. Report "open issues not linked to any asset" as a data-quality finding, not a bug.
3. **Do not walk through meeting items.** 2,450 issue-to-meeting-item links would pull most of the project into every asset. Only issues, forms and documents are walked through.
4. **Depth 3 can explode via shared models.** Door W107 went from 13 to 80 blockers at depth 3, 67 of them via one shared Revit model (asset > form > model > every issue pinned on it). The live build uses `MAX_DEPTH=2`; FOMO1 defaults to 3. Check the blocker paths before trusting depth 3.
5. **"Ready" with nothing linked.** A system with zero links shows ready. Always say so, and show "assets with links" next to the status.
6. **Relationships are not complete.** 2 to 3 of every 19 linked forms are not returned by the Forms API (deleted or no access). Show them as unknown / no access, never as ready.
7. **No asset-to-asset or asset-to-system relationships** exist (`relationships:writable` does not allow them), so system dependencies come from `systems.json`.
8. **Overdue blockers matter.** 18 of 25 blocking issues were past due on Demo project A. Put that in the headline KPIs.
9. **Several copies of each model.** Up to 10 copies of the same Revit model in one project, and assets do not record their source model. Test which copy matches (`model-matching.md`).

## Security

- Client secrets get pasted into chats and meetings. After the first successful run, **regenerate the client secret** in the APS portal and update `.env`.
- Never upload `.env`, `.secrets/` / `.tokens/`, or snapshot and output folders (project data). `.gitignore` covers them.
- The dashboard shows what the signed-in user can see. Share it only in an access-controlled location.
- The live build's `serve.py` gives the browser a token at `/api/token` on 127.0.0.1 only, refuses foreign Host headers and sends no CORS headers. The token is never written into the HTML.
