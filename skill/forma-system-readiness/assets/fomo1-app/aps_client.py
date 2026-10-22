"""Thin read-only APS client: auth header, retries on 429/5xx, throttling, pagination."""
import time

import auth
import simplehttp
from config import S

# Minimum seconds between calls per service (keeps us under documented rate limits)
THROTTLE = {
    "/bim360/relationship": 0.55,   # 120 req/min per user
    "/construction/forms": 0.65,    # 100 req/min per app
    "/construction/issues": 0.13,   # 500 req/min
    "/construction/assets": 0.07,   # 1000 req/min reads
}


class APSError(Exception):
    def __init__(self, status, url, body):
        super().__init__(f"HTTP {status} on {url}: {body}")
        self.status = status
        self.url = url
        self.body = body


class APS:
    def __init__(self):
        self._last = {}
        self.calls = 0

    def _throttle(self, path):
        for prefix, gap in THROTTLE.items():
            if prefix in path:
                wait = self._last.get(prefix, 0) + gap - time.time()
                if wait > 0:
                    time.sleep(wait)
                self._last[prefix] = time.time()
                return

    def request(self, method, path, params=None, json_body=None):
        url = path if path.startswith("http") else S.base_url + path
        force = False
        for attempt in range(6):
            self._throttle(url)
            headers = {
                "Authorization": f"Bearer {auth.get_access_token(force_refresh=force)}",
                "Accept": "application/json",
            }
            if S.region and "/construction/issues" in url:
                headers["x-ads-region"] = S.region
            r = simplehttp.request(method, url, params=params, json_body=json_body, headers=headers, timeout=60)
            self.calls += 1
            if r.status_code == 401 and not force:
                force = True
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                wait = float(r.headers.get("Retry-After") or 2 ** attempt)
                time.sleep(min(wait, 60))
                continue
            if not r.ok:
                raise APSError(r.status_code, r.url, r.text[:500])
            return r.json() if r.content else {}
        raise APSError("retries-exhausted", url, "")

    def get(self, path, params=None):
        return self.request("GET", path, params=params)

    def post(self, path, body=None, params=None):
        # Used only for read-style POSTs (batch-get / search). Phase 1 is read-only.
        return self.request("POST", path, params=params, json_body=body)

    # ---------- pagination ----------
    def iter_items(self, path, params=None, max_pages=5000):
        """Handles ACC styles: pagination.nextUrl, cursorState, offset/totalResults."""
        base = dict(params or {})
        url, cur = path, dict(base)
        for _ in range(max_pages):
            j = self.get(url, cur)
            items = j.get("results")
            if items is None:
                items = j.get("data", [])
            yield from items
            pg = j.get("pagination") or {}
            nxt = pg.get("nextUrl")
            if nxt:
                url = nxt if nxt.startswith("http") else S.base_url + nxt
                cur = None
                continue
            if pg.get("cursorState"):
                url, cur = path, {**base, "cursorState": pg["cursorState"]}
                continue
            total, limit = pg.get("totalResults"), pg.get("limit")
            if total is not None and limit and items:
                off = int(pg.get("offset", 0)) + int(limit)
                if off < int(total):
                    url, cur = path, {**base, "offset": off}
                    continue
            return

    def iter_jsonapi(self, path, params=None, max_pages=1000):
        """Data Management style (data[] + links.next.href)."""
        url, cur = path, params
        for _ in range(max_pages):
            j = self.get(url, cur)
            yield from j.get("data", [])
            nxt = ((j.get("links") or {}).get("next") or {}).get("href")
            if not nxt:
                return
            url, cur = nxt, None

    def iter_relationships(self, container_id, params, max_pages=5000):
        """Relationships search (relationships[] + page.continuationToken)."""
        path = f"/bim360/relationship/v2/containers/{container_id}/relationships:search"
        token = None
        for _ in range(max_pages):
            p = {**params, "pageLimit": 100}
            if token:
                p["continuationToken"] = token
            j = self.get(path, p)
            yield from j.get("relationships", [])
            token = (j.get("page") or {}).get("continuationToken")
            if not token:
                return
