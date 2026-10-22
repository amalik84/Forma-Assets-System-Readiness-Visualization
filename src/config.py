"""Load settings from .env. Standard library only."""

from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
TOKEN_FILE = ROOT / ".tokens" / "token.json"


def _load_env(path=ENV_FILE):
    """Read KEY=VALUE lines into os.environ (existing env vars win)."""
    if not path.exists():
        raise SystemExit(f"Missing {path}. Copy .env.example to .env and fill it in.")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()


def get(key, default=None, required=False):
    value = os.environ.get(key, default)
    if required and not value:
        raise SystemExit(f"{key} is not set in .env")
    return value


CLIENT_ID = get("APS_CLIENT_ID", required=True)
CLIENT_SECRET = get("APS_CLIENT_SECRET", required=True)
CALLBACK_URL = get("APS_CALLBACK_URL", required=True)
SCOPES = get("APS_SCOPES", "data:read")
BASE_URL = get("AUTODESK_FORMA_API_BASE_URL", "https://developer.api.autodesk.com").rstrip("/")
USERINFO_URL = "https://api.userprofile.autodesk.com/userinfo"


def _strip_b(value):
    return value[2:] if value and value.startswith("b.") else value


# Display name of the asset custom attribute that holds the system (docs/05, decision 2026-10-21).
SYSTEM_ATTRIBUTE = get("SYSTEM_ATTRIBUTE", "System Classification")

# Stored without the "b." prefix. Data Management calls add it back (see docs/04).
HUB_ID = _strip_b(get("FORMA_HUB_ID"))
PROJECT_ID = _strip_b(get("FORMA_PROJECT_ID"))


def require_project():
    if not PROJECT_ID or not HUB_ID:
        raise SystemExit("FORMA_HUB_ID and FORMA_PROJECT_ID must be set in .env. See GETTING_STARTED.md, step 3.")


def snapshot_dir(day):
    """data/raw/<projectId>/<YYYY-MM-DD>/: one folder per project, so two projects never mix."""
    require_project()
    return ROOT / "data" / "raw" / PROJECT_ID / day


def snapshot_day():
    """The day a run writes to. refresh.ps1 sets SNAPSHOT_DAY once, so a run that crosses midnight
    keeps all its files in one folder. Without it: today."""
    from datetime import date
    return os.environ.get("SNAPSHOT_DAY") or date.today().isoformat()
