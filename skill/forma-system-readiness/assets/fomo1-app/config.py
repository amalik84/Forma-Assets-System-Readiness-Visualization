"""FOMO1 settings, loaded from .env (no third-party dependency)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_env(BASE_DIR / ".env")


def _get(name, default=""):
    return os.environ.get(name, default).strip()


def _list(name, default=""):
    return [x.strip() for x in _get(name, default).split(",") if x.strip()]


def _bool(name, default="false"):
    return _get(name, default).lower() in ("1", "true", "yes", "y")


class Settings:
    client_id = _get("APS_CLIENT_ID")
    client_secret = _get("APS_CLIENT_SECRET")
    callback_url = _get("APS_CALLBACK_URL", "http://localhost:8080/")
    base_url = _get("AUTODESK_FORMA_API_BASE_URL", "https://developer.api.autodesk.com").rstrip("/")
    scopes = _get("APS_SCOPES", "data:read user-profile:read")

    hub_id = _get("FORMA_HUB_ID")
    project_id = _get("FORMA_PROJECT_ID")
    region = _get("FORMA_REGION")

    group_by = _get("SYSTEM_GROUP_BY", "custom_attribute")
    system_attribute = _get("SYSTEM_ATTRIBUTE_NAME", "System")
    # group_by == "asset_field": use a top-level field of the asset record (see `python fomo1.py probe`)
    system_field = _get("SYSTEM_FIELD_NAME", "")
    systems_endpoint = _get("SYSTEMS_ENDPOINT", "")
    # group_by == "map_file": a CSV exported from Forma (or built by hand) with one row per asset and its system
    system_map_file = BASE_DIR / _get("SYSTEM_MAP_FILE", "system_map.csv")

    issue_closed = set(_list("ISSUE_CLOSED_STATUSES", "closed"))
    issue_warning = set(_list("ISSUE_WARNING_STATUSES", "draft"))
    form_open = set(_list("FORM_OPEN_STATUSES", "inProgress,inReview,draft,in_review"))
    ready_asset_statuses = set(_list("READY_ASSET_STATUSES", ""))
    max_depth = int(_get("MAX_DEPTH", "3") or 3)
    follow_asset_links = _bool("FOLLOW_ASSET_LINKS", "true")

    rel_domains = _list(
        "REL_DOMAINS",
        "autodesk-bim360-asset,autodesk-bim360-issue,"
        "autodesk-bim360-documentmanagement,autodesk-bim360-checklist",
    )

    links = {
        "issue": _get("LINK_ISSUE", "https://acc.autodesk.com/build/issues/projects/{projectId}/issues?preview={id}"),
        "asset": _get("LINK_ASSET", "https://acc.autodesk.com/build/assets/projects/{projectId}/assets?preview={id}"),
        "form": _get("LINK_FORM", "https://acc.autodesk.com/build/forms/projects/{projectId}/forms/{id}"),
        "document": _get("LINK_DOCUMENT", "https://acc.autodesk.com/docs/files/projects/{projectId}?entityId={id}"),
    }

    # system dependency pairs for the topology graph
    systems_file = BASE_DIR / _get("SYSTEMS_FILE", "systems.json")
    # built React dashboard (from ../dashboard-ui). If missing, the plain-HTML fallback is used.
    ui_template = (BASE_DIR / _get("UI_TEMPLATE", "../dashboard-ui/dist/index.html")).resolve()

    output_dir = BASE_DIR / _get("OUTPUT_DIR", "output")
    token_file = BASE_DIR / _get("TOKEN_FILE", ".secrets/tokens.json")

    @classmethod
    def require_credentials(cls):
        missing = [n for n, v in (("APS_CLIENT_ID", cls.client_id),
                                  ("APS_CLIENT_SECRET", cls.client_secret),
                                  ("APS_CALLBACK_URL", cls.callback_url)) if not v]
        if missing:
            raise SystemExit(f"Missing in .env: {', '.join(missing)}")


S = Settings
