"""HTTP helper for APS calls: auth header, retries, rate limits and paging.

Standard library only. Every API module goes through request() so error handling is in one place.
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

import auth
import config

log = logging.getLogger(__name__)

MAX_RETRIES = 5
TIMEOUT_SECONDS = 60
RETRY_STATUSES = {429, 500, 502, 503, 504}


class ApiError(Exception):
    def __init__(self, status, url, detail=""):
        super().__init__(f"{status} on {url} {detail}".strip())
        self.status = status
        self.url = url
        self.detail = detail


def _full_url(path_or_url, params=None):
    url = path_or_url if path_or_url.startswith("http") else config.BASE_URL + path_or_url
    if params:
        sep = "&" if "?" in url else "?"
        url += sep + urllib.parse.urlencode(params, doseq=True)
    return url


def request(method, path_or_url, params=None, body=None):
    """Send one request and return parsed JSON (or None for an empty body).

    - 401: refresh the token once and retry.
    - 429 and 5xx: wait (Retry-After if given, else exponential backoff) and retry.
    - Anything else: raise ApiError with the status and a short detail. Never logs tokens.
    """
    url = _full_url(path_or_url, params)
    data = json.dumps(body).encode() if body is not None else None
    refreshed = False

    for attempt in range(MAX_RETRIES + 1):
        headers = {
            "Authorization": f"Bearer {auth.get_access_token()}",
            "Accept": "application/json",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            short_url = url.split("?")[0]
            if e.code == 401 and not refreshed:
                log.warning("401 on %s, refreshing token once", short_url)
                auth.refresh()
                refreshed = True
                continue
            if e.code in RETRY_STATUSES and attempt < MAX_RETRIES:
                wait = _retry_after(e) or min(2 ** attempt, 30)
                log.warning("%s on %s, retry %d in %ss", e.code, short_url, attempt + 1, wait)
                time.sleep(wait)
                continue
            raise ApiError(e.code, short_url, detail) from None
        except urllib.error.URLError as e:
            if attempt < MAX_RETRIES:
                time.sleep(min(2 ** attempt, 30))
                continue
            raise ApiError(0, url.split("?")[0], str(e.reason)) from None
    raise ApiError(0, url.split("?")[0], "retries exhausted")


def _retry_after(error):
    value = error.headers.get("Retry-After") if error.headers else None
    try:
        return max(1, int(float(value)))
    except (TypeError, ValueError):
        return None


def get_json(path_or_url, params=None):
    return request("GET", path_or_url, params=params)


def post_json(path_or_url, body, params=None):
    """Only for read-style POSTs (searches, batch-get). Phase 1 is read only."""
    return request("POST", path_or_url, params=params, body=body)


# ---------- paging ----------

def get_all_jsonapi(path, params=None):
    """Data Management: follow links.next.href and collect 'data'."""
    items, url, first = [], path, True
    while url:
        page = get_json(url, params if first else None)
        first = False
        items.extend(page.get("data", []))
        url = ((page.get("links") or {}).get("next") or {}).get("href")
    return items


def get_all_offset(path, params=None, limit=100, results_key="results"):
    """Issues, Forms and ACC Admin: limit/offset paging, stops when a page is short."""
    params = dict(params or {})
    items, offset = [], 0
    while True:
        page = get_json(path, {**params, "limit": limit, "offset": offset})
        batch = page.get(results_key) or page.get("data") or []
        items.extend(batch)
        total = (page.get("pagination") or {}).get("totalResults")
        offset += len(batch)
        if not batch or len(batch) < limit or (total is not None and offset >= total):
            return items


def get_all_cursor(path, params=None, limit=200, results_key="results"):
    """Assets and Relationships: follow pagination.nextUrl (or cursorState) until absent."""
    params = dict(params or {}, limit=limit)
    items, url, first = [], path, True
    while url:
        page = get_json(url, params if first else None)
        first = False
        items.extend(page.get(results_key) or [])
        pagination = page.get("pagination") or page.get("page") or {}
        next_url = pagination.get("nextUrl")
        cursor = pagination.get("cursorState")
        if next_url:
            url = next_url
        elif cursor:
            url = _full_url(path, {**params, "cursorState": cursor})
        else:
            url = None
    return items
