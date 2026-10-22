# 07. Build guide, step by step

> This is the history of how the tool was built. **To use it, follow `GETTING_STARTED.md`** in the project root.

Work through the steps in order. Each step has a prompt you can give Claude Code in this folder, and a check that tells you it worked. Tick the box when done.

---

## Step 0. Project setup ✅ (done 2026-10-21)

Folder, `CLAUDE.md`, `docs/`, `.env`, `.env.example`, `.gitignore`, git repo.

- [x] Done

## Step 1. Check the APS app settings (you, 5 min)

In https://aps.autodesk.com/myapps, open the app and confirm:

- Callback URL is exactly `http://localhost:8080/`
- APIs enabled include Data Management and Autodesk Construction Cloud
- In Forma Account Admin > Custom Integrations, the client ID is active for the account that holds the target project

- [ ] Done

## Step 2. Login and "who am I"

Status: done for Assets, Issues, Forms, Relationships. Data Management pending (open question 9).

Code done 2026-10-21 (`src/config.py`, `src/auth.py`, `src/aps_client.py`, `src/whoami.py`). Client credentials and callback URL verified against APS. Login works (2026-10-21). Project confirmed: **Demo project A** (ACC, active, account `<id>`).

API access (3-legged, 2026-10-21): Assets OK, Issues OK, Forms OK, Relationships OK. **Data Management 403** (`BIM360DM_ERROR`, also with an app-only token). The integration is active on the account (ACC Admin API answers with an app-only token), so Data Management access looks switched off in the custom integration. Step 2 is done apart from that; steps 3 to 5 can go ahead. Documents (step 6) need Data Management.

**Prompt:** "Do step 2 of the build guide: set up the venv and requirements, write `src/auth.py` with `login` and `refresh` commands, and a `src/whoami.py` that prints my name, the hubs and the projects I can see."

**Check:** `py src/auth.py login` opens the browser, you sign in, the terminal says "Logged in". `py src/whoami.py` shows your name, hubs and projects, and ends with "OK: hub and project in .env are reachable".

- [ ] Done

## Step 3. API client and discovery run

**Prompt:** "Do step 3: write `src/aps_client.py` (paging, retries, 429, 401) and a `src/discover.py` that pulls a small sample from Assets, Systems, Relationships, Issues and Forms into `data/raw/discovery/`. Then update `docs/04-api-reference.md`: mark verified endpoints as known and fill in the relationship domain/type table from real data."

**Check:** JSON files in `data/raw/discovery/`. The domain/type table in doc 04 is filled in from real responses.

Done 2026-10-21. `src/aps_client.py` (retries, 401 refresh, 429, three paging styles) and `src/discover.py` (`py src/discover.py`). Paging tested on full sets: 6,516 assets, 332 issues, 147 forms. Doc 04 updated. **Finding that blocks step 4:** no Systems API, see open question 2.

- [x] Done

## Step 4. Systems and assets

**Prompt:** "Do step 4: write `src/fetch/assets.py` to get all systems, assets, categories and statuses, and map assets to systems. Use what we found in discovery."

**Check:** Counts match what you see in Forma for the project. Open question 2 (how systems are modelled) is answered.

Done 2026-10-21. `py src/fetch/assets.py` (26 s) writes `data/raw/<projectId>/YYYY-MM-DD/assets.json`. Demo project A: 6,516 active assets, 2 systems from `System Classification` (`B10` 257 assets, `Supply Air` 1), 6,258 without a system. 6 unit tests pass (`py -m unittest discover tests`). **To confirm by you:** 6,516 matches the asset count in Forma.

- [x] Done

## Step 5. Issues and forms

**Prompt:** "Do step 5: fetch all issues and forms for the project with paging, and normalise them to the shapes in doc 05."

**Check:** Issue and form counts match the Forma UI (with no filters applied).

Done 2026-10-21. `py src/fetch/issues.py` and `py src/fetch/forms.py` write `issues.json` and `forms.json` to `data/raw/<projectId>/YYYY-MM-DD/`. Demo project A: **332 issues** (317 not closed), **147 forms** (89 not submitted). `FORM_DONE_STATUSES=submitted` set in `.env` (proposed, open question 4). 12 unit tests pass. **To confirm by you:** 332 and 147 match Forma with no filters.

- [x] Done

## Step 6. Relationships and documents

**Prompt:** "Do step 6: fetch all relationships for the project and the metadata for referenced documents. Save the edge list."

**Check:** Pick one asset you know has linked items in Forma. The edge list shows the same links.

Done 2026-10-21. `py src/fetch/relationships.py` (7,848 relationships, 40 s) and `py src/fetch/documents.py` (181 documents, all with names, plus 224 issue pins as extra edges). 19 unit tests pass. **To confirm by you:** asset **Door - Interior - Double [1263119]** (barcode W107) shows 2 issues (#130, #175), 15 forms and 2 documents in Forma; 2 of its linked forms are not returned by the Forms API.

- [x] Done

## Step 7. Graph and readiness

**Decide first:** open questions 3, 4 and 5 in doc 08.

**Prompt:** "Do step 7: build `model.py` and `readiness.py` as in doc 05, with unit tests on small hand-made fixtures, including a three-level chain and a loop."

**Check:** Tests pass. Manually check 3 systems against Forma.

Done 2026-10-21. `py src/readiness.py` (under 1 s) writes `data/raw/<projectId>/YYYY-MM-DD/readiness.json`. 30 unit tests pass (three-level chain, loop, depth limit, shortest path, stop at assets, info types never block). Questions 3 and 4 still run on the proposed values (`closed`, `submitted`).

Demo project A at depth 2: **B10 ready** (257 assets, but none has any link), **Supply Air not ready** (forms #193 and #194, both `inReview`), (no system) 30 assets not ready, 13 unknown. Only 2 systems exist, so check those 2 plus asset W107 (13 blockers) against Forma.

- [x] Done

## Step 8. Dashboard

**Prompt:** "Do step 8: build `render.py` and `templates/dashboard.html.j2` as in doc 06. Then open it in the preview so I can click through."

**Check:** Click a system, see assets; click an asset, see references with paths and working "Open in Forma" links.

Done 2026-10-21. `py src/render.py` writes `dashboard/index.html` (open it by double-clicking). Clicked through in the preview: Supply Air shows forms #193 and #194 as blocking; W107 shows 6 issues and 17 forms, with paths such as "via Arc and electrical.nwd". No console errors. **To check by you:** click a few "Open in Forma" links for an issue, a form and an asset (open question 11).

- [x] Done

## Step 8b. Lifecycle, graph and live viewer (added 2026-10-21)

Done 2026-10-21, based on the a tunnel concept. See doc 06, "Version 2". New: `src/lifecycle.py`, `src/fetch/models.py`, `src/serve.py`; lifecycle steps in `src/fetch/assets.py`; phase and path keys in `src/readiness.py`. 39 unit tests pass. Clicked through in the preview with the live viewer: W107 found and coloured in Arch_demo, graph node and phase filters work, picking an element in the model selects its asset, no console errors.

**Check by you:** run `py src/serve.py`, open http://127.0.0.1:8765, click around. Is the phase mapping in `src/lifecycle.py` right for the team?

- [x] Done

## Step 9. Daily run

**Prompt:** "Do step 9: write `src/run_daily.py` (fetch assets, issues, forms, relationships, documents, models; readiness; render) and a `run_daily.bat`, add logging, then give me the Task Scheduler command to run it at 06:00 every weekday."

**Check:** The task runs the next morning, the log shows success and the dashboard date updates. Answer open questions 6, 7 and 8.

- [ ] Done

---

## Phase 2 (later)

- Add `data:write` scope, re-login.
- "Raise issue" from an asset in the dashboard. Needs a small local server or a separate script, since a static page cannot call the API safely.
