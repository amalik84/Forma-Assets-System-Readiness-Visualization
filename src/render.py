"""Turn a day's readiness.json into the static dashboard (docs/06).

Usage (from the project folder): py src/render.py [YYYY-MM-DD]
Writes dashboard/index.html (data embedded, opens by double-click), dashboard/data.json and
dashboard/fonts/. No API calls except an optional "who am I" for the header.
"""

import json
import shutil
import sys
from datetime import datetime

import config

TEMPLATE = config.ROOT / "templates" / "dashboard.html"
FONTS = config.ROOT / "assets" / "fonts"
OUT = config.ROOT / "dashboard"


def link(template_key, item_id):
    template = config.get(template_key)
    return template.format(projectId=config.PROJECT_ID, id=item_id) if template else None


def slim_reference(r):
    """Only what the browser needs, to keep the page small."""
    typ, item_id = r["key"].split(":", 1)
    url = r.get("url")
    if typ == "issue" and r.get("resolved"):
        url = link("FORMA_ISSUE_URL", item_id)
    elif typ == "form" and r.get("resolved"):
        url = link("FORMA_FORM_URL", item_id)
    keys = r.get("pathKeys") or []
    out = {"key": r["key"], "type": typ, "typeLabel": r["typeLabel"], "label": r["label"], "state": r["state"],
           "depth": r["depth"], "path": r["path"], "url": url, "phase": r.get("phase", "execution"),
           # The item just before this one on the path, so the graph can draw asset > document > issue.
           "via": keys[-2] if len(keys) > 1 else None}
    for key in ("status", "itemType", "dueDate"):
        if r.get(key):
            out[key] = r[key]
    return out


def build_data(readiness, user=None, models=None):
    assets = []
    open_issues, open_forms = set(), set()
    for a in readiness["assets"]:
        refs = a.get("references") or []
        for r in refs:
            if r["state"] == "blocking":
                (open_issues if r["type"] == "issue" else open_forms).add(r["key"])
        assets.append({
            "id": a["id"], "name": a["name"], "barcode": a.get("barcode"), "category": a.get("category"),
            "assetStatus": a.get("assetStatus"), "status": a["status"], "systemIds": a["systemIds"],
            "lifecycleSetId": a.get("lifecycleSetId"), "lifecycleStep": a.get("lifecycleStep"),
            "blockingCount": a["blockingCount"], "unknownCount": a["unknownCount"], "refCount": len(refs),
            "url": link("FORMA_ASSET_URL", a["id"]),
            "references": [slim_reference(r) for r in refs],
        })
    systems = [{k: s[k] for k in ("id", "name", "status", "assetIds", "isUnassigned", "assetCount",
                                  "assetsNotReady", "assetsUnknown", "assetsWithReferences", "blockingCount")}
               for s in readiness["systems"]]
    meta = dict(readiness["meta"])
    generated = datetime.fromisoformat(meta["generatedAt"]).astimezone()
    meta.update({
        "projectName": config.get("FORMA_PROJECT_NAME") or config.PROJECT_ID,
        "generatedAtLocal": generated.strftime("%d %B %Y, %H:%M"),
        "user": user,
        "openIssuesLinked": len(open_issues),
        "openFormsLinked": len(open_forms),
    })
    viewable = [{"name": m["name"], "versionNumber": m["versionNumber"], "urn": m["derivativeUrn"]}
                for m in (models or {}).get("models", []) if m.get("status") == "success" and m.get("derivativeUrn")]
    return {"meta": meta, "systems": systems, "assets": assets, "phases": readiness.get("phases", []),
            "lifecycleSets": readiness.get("lifecycleSets", {}), "models": viewable}


def render(data):
    html = TEMPLATE.read_text(encoding="utf-8")
    # Embedded JSON must not close the <script> tag early.
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(html.replace("/*__DATA__*/", payload), encoding="utf-8")
    (OUT / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    if FONTS.exists():
        shutil.copytree(FONTS, OUT / "fonts", dirs_exist_ok=True)
    return OUT / "index.html"


def who_am_i():
    """Name for the header. Never fails the render."""
    try:
        import aps_client
        info = aps_client.get_json(config.USERINFO_URL)
        return info.get("name")
    except Exception:  # noqa: BLE001 - header detail only
        return None


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else config.snapshot_day()
    path = config.snapshot_dir(day) / "readiness.json"
    if not path.exists():
        raise SystemExit(f"{path} not found. Run py src/readiness.py first.")
    models_path = path.parent / "models.json"
    models = json.loads(models_path.read_text(encoding="utf-8")) if models_path.exists() else None
    data = build_data(json.loads(path.read_text(encoding="utf-8")), user=who_am_i(), models=models)
    out = render(data)
    size_kb = out.stat().st_size // 1024
    print(f"Dashboard written: {out} ({size_kb} KB)")
    print(f"Systems {len(data['systems'])}, assets {len(data['assets'])}, "
          f"open issues linked {data['meta']['openIssuesLinked']}, open forms linked {data['meta']['openFormsLinked']}")


if __name__ == "__main__":
    main()
