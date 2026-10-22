"""FOMO1 command line.

  python fomo1.py login      one-time browser sign-in (3-legged OAuth)
  python fomo1.py whoami     show signed-in Autodesk user
  python fomo1.py hubs       list hubs you can access
  python fomo1.py projects   list projects in FORMA_HUB_ID (or --hub)
  python fomo1.py check      smoke-test every API FOMO1 uses
  python fomo1.py run        pull data + build output/dashboard.html (daily job)
  python fomo1.py demo       build a dashboard from fake data (no login needed)
"""
import argparse
import csv
import json
import logging
import random
import sys
import time
import webbrowser

from config import S

LOG = logging.getLogger("fomo1")


def setup_logging():
    S.output_dir.mkdir(parents=True, exist_ok=True)
    (S.output_dir / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(S.output_dir / "logs" / "fomo1.log", encoding="utf-8")],
    )


def cmd_login(_):
    import auth
    auth.login()


def cmd_whoami(_):
    from aps_client import APS, APSError
    api = APS()
    for url in ("https://api.aps.autodesk.com/userinfo", f"{S.base_url}/userinfo",
                f"{S.base_url}/userprofile/v1/users/@me"):
        try:
            j = api.get(url)
            print(json.dumps({k: j.get(k) for k in ("name", "email", "preferred_username", "sub",
                                                     "userName", "emailId", "userId") if j.get(k)}, indent=2))
            return
        except APSError as e:
            LOG.info("whoami via %s failed (%s)", url, e.status)
    print("Could not read user profile (check APS_SCOPES includes user-profile:read).")


def cmd_hubs(_):
    from aps_client import APS
    for h in APS().iter_jsonapi("/project/v1/hubs"):
        a = h["attributes"]
        print(f"{h['id']}\t{a.get('name')}\t{a.get('region', '')}\t{(a.get('extension') or {}).get('type', '')}")


def cmd_projects(args):
    from aps_client import APS
    hub = args.hub or S.hub_id
    if not hub:
        raise SystemExit("Give --hub b.xxxx or set FORMA_HUB_ID in .env")
    for p in APS().iter_jsonapi(f"/project/v1/hubs/{hub}/projects", {"page[limit]": 200}):
        print(f"{p['id']}\t{p['attributes'].get('name')}")


def cmd_check(_):
    from aps_client import APS, APSError
    from collector import bare
    api, pid = APS(), bare(S.project_id)
    tests = [
        ("Hubs (Data Management)", "/project/v1/hubs", None),
        ("Project", f"/project/v1/hubs/{S.hub_id}/projects/b.{pid}", None),
        ("Issues", f"/construction/issues/v1/projects/{pid}/issues", {"limit": 1}),
        ("Issue permissions (users/me)", f"/construction/issues/v1/projects/{pid}/users/me", None),
        ("Assets v2", f"/construction/assets/v2/projects/{pid}/assets", {"limit": 1}),
        ("Asset categories", f"/construction/assets/v1/projects/{pid}/categories", None),
        ("Asset custom attributes", f"/construction/assets/v1/projects/{pid}/custom-attributes", {"limit": 50}),
        ("Forms v2", f"/construction/forms/v2/projects/{pid}/forms", {"limit": 1}),
        ("Forms v1 (fallback)", f"/construction/forms/v1/projects/{pid}/forms", {"limit": 1}),
        ("Relationships search", f"/bim360/relationship/v2/containers/{pid}/relationships:search",
         {"domain": "autodesk-bim360-asset", "pageLimit": 1}),
        ("Relationship domains", "/bim360/relationship/v2/utility/relationships:writable", None),
    ]
    for name, path, params in tests:
        try:
            j = api.get(path, params)
            extra = ""
            if "custom-attributes" in path:
                extra = " | attributes: " + ", ".join(a.get("displayName", "?") for a in j.get("results", []))
            print(f"  OK    {name}{extra}")
        except APSError as e:
            print(f"  FAIL  {name}  -> HTTP {e.status}: {str(e.body)[:160]}")


def _history_append(snapshot):
    path = S.output_dir / "history.csv"
    s = snapshot["summary"]
    row = {"date": snapshot["meta"]["generatedAt"], **s}
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if new:
            w.writeheader()
        w.writerow(row)
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))[-60:]


def _history_read():
    path = S.output_dir / "history.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))[-60:]


def _seed_demo_history(snap):
    """Fake 20 days of history so the demo trend chart has something to show."""
    path = S.output_dir / "history.csv"
    S.output_dir.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    rnd = random.Random(3)
    s = snap["summary"]
    now = time.time()
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", *s.keys()])
        w.writeheader()
        for i in range(20, 0, -1):
            row = dict(s)
            row["openIssues"] = s["openIssues"] + int(i * 0.9) + rnd.randint(0, 3)
            row["openForms"] = s["openForms"] + int(i * 0.5) + rnd.randint(0, 2)
            w.writerow({"date": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now - i * 86400)), **row})


def _write_outputs(raw, open_browser=False, demo=False, track=True):
    import dashboard
    import readiness
    snap = readiness.build_snapshot(raw)
    if demo:
        _seed_demo_history(snap)
    snap["history"] = _history_append(snap) if track else _history_read()
    day = snap["meta"]["generatedAt"][:10]
    snaps = S.output_dir / "snapshots"
    snaps.mkdir(parents=True, exist_ok=True)
    for p in (snaps / f"snapshot_{day}.json", S.output_dir / "latest.json"):
        p.write_text(json.dumps(snap, indent=1, default=str), encoding="utf-8")
    html_path = S.output_dir / "dashboard.html"
    html_path.write_text(dashboard.render(snap), encoding="utf-8")
    s = snap["summary"]
    LOG.info("Systems ready %s/%s | assets clear %s/%s | open issues %s | open forms %s",
             s["systemsReady"], s["systems"], s["assetsReady"], s["assets"], s["openIssues"], s["openForms"])
    LOG.info("Dashboard: %s", html_path)
    if open_browser:
        webbrowser.open(html_path.as_uri())


def cmd_run(args):
    from aps_client import APS
    from collector import collect
    raw = collect(APS())
    (S.output_dir / "raw_latest.json").write_text(json.dumps(raw, default=str), encoding="utf-8")
    _write_outputs(raw, args.open)


def cmd_regroup(args):
    """Rebuild everything from output/raw_latest.json using the current .env / system map. No Forma calls, seconds."""
    src = S.output_dir / "raw_latest.json"
    if not src.exists():
        raise SystemExit("No output/raw_latest.json yet. Run `python fomo1.py run` first.")
    raw = json.loads(src.read_text(encoding="utf-8"))
    _write_outputs(raw, args.open, track=False)
    import readiness  # noqa: F401  (prints nothing; keeps import order explicit)
    snap = json.loads((S.output_dir / "latest.json").read_text(encoding="utf-8"))
    sm = snap["meta"].get("systemMap")
    if sm:
        LOG.info("System map: %d rows in file, %d assets matched of %d", sm["rows"], sm["matched"], snap["summary"]["assets"])


def cmd_render(args):
    """Rebuild dashboard.html from output/latest.json (no API calls, no login)."""
    import dashboard
    src = S.output_dir / "latest.json"
    if not src.exists():
        raise SystemExit("No output/latest.json yet. Run `python fomo1.py run` first.")
    snap = json.loads(src.read_text(encoding="utf-8"))
    import readiness
    # always re-read systems.json so edits show up without pulling from Forma again
    snap["topology"] = readiness.load_topology({s["name"] for s in snap["systems"]})
    out = S.output_dir / "dashboard.html"
    out.write_text(dashboard.render(snap), encoding="utf-8")
    LOG.info("Dashboard rebuilt from latest.json using %s: %s", dashboard.which_template(), out)
    if args.open:
        webbrowser.open(out.as_uri())


def cmd_probe(_):
    """Find where Forma keeps asset SYSTEMS: prints one full asset record and tests candidate endpoints."""
    from aps_client import APS, APSError
    from collector import bare
    api, pid = APS(), bare(S.project_id)
    print("1) One full asset record from the Assets v2 API (look for anything system-like):\n")
    j = api.get(f"/construction/assets/v2/projects/{pid}/assets", {"limit": 1, "includeCustomAttributes": "true"})
    rec = (j.get("results") or [{}])[0]
    print(json.dumps(rec, indent=2, ensure_ascii=False)[:3500])
    print("\n   top-level keys:", ", ".join(sorted(rec.keys())))
    print("\n2) Candidate systems endpoints (HTTP status; 200 = exists):\n")
    cands = [f"/construction/assets/v1/projects/{pid}/systems", f"/construction/assets/v2/projects/{pid}/systems",
             f"/construction/systems/v1/projects/{pid}/systems", f"/construction/systems/v2/projects/{pid}/systems",
             f"/construction/assets/v1/projects/{pid}/asset-systems", f"/construction/commissioning/v1/projects/{pid}/systems"]
    for path in cands:
        try:
            r = api.get(path, {"limit": 3})
            print(f"  200  {path}\n       {json.dumps(r, ensure_ascii=False)[:300]}")
        except APSError as e:
            print(f"  {e.status}  {path}")
        except Exception as e:  # network etc.
            print(f"  ERR  {path}  {e}")
    print("\nSend this whole output back (it contains project data but no credentials).")


def cmd_fields(_):
    """Help choose how to group assets into systems. Reads output/raw_latest.json (no API calls)."""
    from collections import Counter
    path = S.output_dir / "raw_latest.json"
    if not path.exists():
        raise SystemExit("Run `python fomo1.py run` first.")
    raw = json.loads(path.read_text(encoding="utf-8"))
    assets = raw["assets"]
    total = len(assets)
    print(f"{total} assets\n")
    cats = Counter(raw["categories"].get(a.get("categoryId"), "(none)") for a in assets)
    print(f"CATEGORY (SYSTEM_GROUP_BY=category): {len(cats)} distinct values")
    for v, n in cats.most_common(12):
        print(f"   {n:6d}  {v}")
    print("\nCUSTOM ATTRIBUTES (SYSTEM_GROUP_BY=custom_attribute), best filled first:")
    key_to_name = {v: k for k, v in raw["attrDefs"].items()}
    rows = []
    for key, name in key_to_name.items():
        vals = [str(a["customAttributes"][key]) for a in assets
                if str(a.get("customAttributes", {}).get(key) or "").strip()]
        if vals:
            rows.append((len(vals), name, Counter(vals)))
    for n, name, c in sorted(rows, key=lambda r: -r[0])[:15]:
        top = ", ".join(f"{v} ({k})" for v, k in c.most_common(4))
        print(f"   {n:6d} filled ({n * 100 // total:3d}%) | {len(c):5d} distinct | {name}: {top[:110]}")
    extras = Counter()
    for a in assets:
        for k, v in (a.get("extra") or {}).items():
            if v not in (None, "", [], {}):
                extras[k] += 1
    if extras:
        print("\nOTHER ASSET FIELDS returned by Forma (use SYSTEM_GROUP_BY=asset_field + SYSTEM_FIELD_NAME=<name>):")
        for k, n in extras.most_common(15):
            sample = Counter(json.dumps(a["extra"][k], ensure_ascii=False)[:50] for a in assets if (a.get("extra") or {}).get(k) not in (None, "", [], {}))
            print(f"   {n:6d} filled ({n * 100 // total:3d}%) | {len(sample):5d} distinct | {k}: {', '.join(v for v, _ in sample.most_common(3))}")
    print("\nA good system field is filled on most assets and has a modest number of distinct values (about 3-50).")


def cmd_demo(args):
    """Fake but realistic project so the team can see the dashboard before connecting."""
    rnd = random.Random(7)
    S.group_by, S.system_attribute = "custom_attribute", "System"   # demo ignores .env grouping
    S.output_dir = S.output_dir / "demo"   # never touch real run data
    S.output_dir.mkdir(parents=True, exist_ok=True)
    S.systems_file = S.output_dir / "systems.json"
    S.systems_file.write_text(json.dumps({"placeholder": False, "feeds": [
        ["Electrical", "HVAC"], ["Electrical", "Fire Protection"], ["Electrical", "Vertical Transport"],
        ["Plumbing", "Fire Protection"], ["HVAC", "Vertical Transport"]]}), encoding="utf-8")
    systems = {"HVAC": ["AHU", "FCU", "VAV Box", "Chiller"], "Electrical": ["Switchboard", "Panelboard", "UPS"],
               "Fire Protection": ["Sprinkler Riser", "Fire Pump", "Alarm Panel"], "Plumbing": ["Booster Pump", "Water Heater"],
               "Vertical Transport": ["Elevator"]}
    issue_titles = ["Missing label", "Insulation damaged", "Commissioning test failed", "Wrong model installed",
                    "Access panel blocked", "Cable tray clash", "Vibration out of tolerance", "O&M manual missing"]
    statuses = ["open", "in_progress", "in_review", "closed", "closed", "closed", "pending", "completed", "draft"]
    raw = {"meta": {"hubId": "b.demo-hub", "projectId": "demo-project", "projectName": "DEMO · Tower A Fit-out",
                    "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"), "formsApi": "v2", "apiCalls": 0, "durationSec": 0},
           "categories": {}, "assetStatuses": {"s1": "Installed", "s2": "Commissioned", "s3": "Ordered"},
           "attrDefs": {"System": "ca1"}, "assets": [], "issues": {}, "forms": {}, "relationships": [], "docNames": {}}
    A, I, F, D = "autodesk-bim360-asset", "autodesk-bim360-issue", "autodesk-construction-form", "autodesk-bim360-documentmanagement"
    n_issue = n_form = 0
    for sname, kinds in systems.items():
        for kind in kinds:
            cid = f"cat-{kind}"
            raw["categories"][cid] = kind
            for k in range(rnd.randint(1, 4)):
                aid = f"a-{sname[:3]}-{kind[:3]}-{k}".replace(" ", "")
                raw["assets"].append({"id": aid, "name": f"{kind.upper().replace(' ', '-')}-{rnd.randint(100, 999)}",
                                      "description": f"{kind} · Level {rnd.randint(1, 12)}", "categoryId": cid,
                                      "statusId": rnd.choice(["s1", "s2", "s3"]), "customAttributes": {"ca1": sname}})
                doc = f"urn:adsk.wipprod:dm.lineage:{aid}-spec"
                raw["docNames"][doc] = f"{kind} submittal - {rnd.choice(['Rev A', 'Rev B', 'Rev C'])}.pdf"
                raw["relationships"].append([[A, "asset", aid], [D, "documentlineage", doc]])
                for _ in range(rnd.randint(0, 3)):
                    n_issue += 1
                    iid = f"i{n_issue}"
                    st = rnd.choice(statuses if sname != "Plumbing" else ["closed"])
                    raw["issues"][iid] = {"id": iid, "displayId": n_issue, "title": rnd.choice(issue_titles), "status": st,
                                          "dueDate": f"2026-{rnd.choice(['09', '10', '11', '12'])}-{rnd.randint(1, 28):02d}",
                                          "type": rnd.choice(["Commissioning", "Quality / Defect", "Safety", "Documentation", "Coordination"]),
                                          "linkedDocUrns": [doc] if rnd.random() < .4 else []}
                    if not raw["issues"][iid]["linkedDocUrns"]:
                        raw["relationships"].append([[A, "asset", aid], [I, "issue", iid]])
                if rnd.random() < .6:
                    n_form += 1
                    fid = f"f{n_form}"
                    raw["forms"][fid] = {"id": fid, "name": rnd.choice(["Pre-functional checklist", "Start-up form", "Functional test"]),
                                         "status": rnd.choice(["closed", "closed", "inProgress", "inReview"]) if sname != "Plumbing" else "closed",
                                         "formNum": n_form, "template": "Commissioning"}
                    raw["relationships"].append([[A, "asset", aid], [F, "form", fid]])
    for extra in range(5):
        n_issue += 1
        raw["issues"][f"i{n_issue}"] = {"id": f"i{n_issue}", "displayId": n_issue, "title": "Unlinked site issue",
                                        "status": "open", "linkedDocUrns": []}
    S.links = {k: None for k in S.links}
    _write_outputs(raw, args.open, demo=True)


def main():
    p = argparse.ArgumentParser(description="FOMO1 - Forma system readiness")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("login", "whoami", "hubs", "check", "run", "demo", "fields", "render", "probe", "regroup"):
        sp = sub.add_parser(name)
        if name in ("run", "demo", "render", "regroup"):
            sp.add_argument("--open", action="store_true", help="open dashboard in browser")
    sp = sub.add_parser("projects")
    sp.add_argument("--hub")
    args = p.parse_args()
    setup_logging()
    {"login": cmd_login, "whoami": cmd_whoami, "hubs": cmd_hubs, "projects": cmd_projects,
     "check": cmd_check, "run": cmd_run, "demo": cmd_demo, "fields": cmd_fields, "render": cmd_render, "probe": cmd_probe, "regroup": cmd_regroup}[args.cmd](args)


if __name__ == "__main__":
    main()
