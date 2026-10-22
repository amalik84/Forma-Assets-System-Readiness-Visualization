# 01. Project brief

Source: internal kick-off call, 2026-10-21 (recording transcript). Items marked *assumption* were not stated in the call.

## Problem

Before a system (for example HVAC zone 3, fire alarm, a substation) can be launched or handed over, the team needs to know that nothing linked to it is still open. Today that means clicking through assets, issues, forms and documents in Forma by hand, and references that sit several levels deep are easy to miss.

## Goal

A visual dashboard that shows, per system, whether it is ready to launch, and lets you drill down:

**Project > Systems > Assets > References (issues, forms, documents, and what those link to)**

## Users

- Project and commissioning teams who decide whether a system is ready *(assumption)*
- Each user only sees data their Forma permissions allow

## Scope

### Phase 1 (this build): read only

1. Log in to Forma through APS (3-legged OAuth). Identify who I am, which hub and which project.
2. Read through the APIs:
   - Data Management (hubs, projects, folders, documents)
   - Assets (assets, categories, statuses, systems)
   - Relationships (what is linked to what)
   - Issues
   - Forms
3. Build the reference graph per asset, following relationships through multiple levels.
4. Work out readiness per asset and per system.
5. Generate a visual dashboard: click a system, see its assets, click an asset, see all its references.
6. Run as a plain script every morning, no AI involved.

### Phase 2 (later)

- Raise issues from findings in the dashboard (write access to the Issues API).
- Possibly notifications or a summary email *(assumption)*.

### Out of scope

- Editing assets, forms or documents
- Any data flowing outside the user's Forma permissions

## Success criteria *(proposed, to confirm)*

- Every system in the chosen project appears with a ready / not ready / unknown status.
- For a not-ready system, you can reach the blocking issue or form in two clicks and open it in Forma.
- The daily run finishes without manual steps for at least 14 days in a row.
- Numbers match a manual check of 3 sample systems.

## Inputs already available

- Custom integration in Forma, already activated in Account Admin.
- APS app: client ID, client secret, callback URL `http://localhost:8080/` (stored in `.env`).
