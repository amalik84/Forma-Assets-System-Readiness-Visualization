# Forma Assets System Readiness Visualization

**Is this system ready to launch?** A read-only dashboard for an Autodesk Forma (ACC / Autodesk Build) project. For every asset it follows Forma's links (asset > document > issue, asset > form > issue) to the issues and forms that are still open, and rolls them up per system.

Work in progress, shared as is. Not an official Autodesk product and not supported by Autodesk. Tested on demo projects only.

## What you get

- **Systems and assets:** ready / not ready / unknown per system and per asset, with the blocking items and why each one is linked.
- **Lifecycle band:** linked items per phase (Design, Execution, Handover and operations) and where the assets are in their Forma status set.
- **Relationship graph** around the selected asset.
- **Live 3D viewer** (APS Viewer): the selected asset or system coloured by readiness in the project's models.
- **Power BI version** of the same results (three report pages, refreshed with the rest), for teams that work in Power BI.
- Daily refresh is a plain Python script, **no AI** at runtime. Python standard library only, no `pip install`.

## Repository layout

| Path | What |
|---|---|
| `src/` | Python pipeline: login (`auth.py`), fetch (`fetch/`), graph and readiness (`model.py`, `readiness.py`), dashboard (`render.py`), local server for the viewer (`serve.py`) |
| `templates/dashboard.html` | Dashboard page; `render.py` embeds the data |
| `refresh.ps1`, `serve.ps1` | Refresh everything, and serve the dashboard on http://127.0.0.1:8765 |
| `src/export_powerbi.py`, `src/powerbi_project.py`, `powerbi_refresh.ps1` | Power BI tables and project in `data/powerbi/`, and a no-click refresh of the open project |
| `src/survey.py` | Helps choose `SYSTEM_ATTRIBUTE` and `VIEWER_MODELS` for a new project |
| `GETTING_STARTED.md` | Step-by-step guide for new users |
| `CONTRIBUTING.md`, `LICENSE` | How to suggest improvements; MIT-0 licence |
| `docs/` | Build history: brief, architecture, auth, API reference, data model, dashboard spec, build guide, decisions and open questions |
| `tests/` | `py -m unittest discover tests` |
| `skill/forma-system-readiness/` | Claude skill that walks you through running or setting it up. Also bundles **FOMO1**, a portable version (GO / CONDITIONAL / NO-GO board, system dependencies, scheduler) |

## Getting started

**New user? Follow [GETTING_STARTED.md](GETTING_STARTED.md).** It covers what you and your Forma admin need, then nine short steps with what success looks like, and a table for every error seen so far.

In short:

```powershell
copy .env.example .env          # your APS client ID and secret, Forma hub and project
py src\auth.py login            # sign in in the browser
py src\whoami.py                # every API should say OK
py src\survey.py                # choose how assets are grouped into systems
.\refresh.ps1                   # fetch, readiness, render
.\serve.ps1                     # open the dashboard with the live viewer
```

Or install `skill/forma-system-readiness` in Claude and ask it to set this up for your project.

## Good to know

- Read only: nothing is written to Forma.
- The dashboard shows what **your** login can see. Share outputs only in access-controlled places.
- Never commit `.env`, `.tokens/`, `data/` or `dashboard/` (ignored by `.gitignore`).
- The dashboard uses Arial unless you add the Artifakt fonts locally (`assets/fonts/README.md`). Font files are not included.
- Project names in the docs are anonymised ("Demo project A, B, C"). Real IDs, names and data stay in your local `.env` and `data/`.

## Improve it together

Found a bug, have an idea, or got it running on a new project? Please share it **here** rather than starting your own copy: open an issue, start a Discussion, or send a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md). One shared version stays better tested for everyone.

## Licence

[MIT No Attribution (MIT-0)](LICENSE): free to use, change and share, including commercially, with no need to credit anyone. Provided as is, without warranty.
