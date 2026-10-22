"""APS OAuth v2, 3-legged (authorization code) + refresh token.

- `login()` runs once interactively: opens the browser, catches the code on
  APS_CALLBACK_URL (http://localhost:8080/), exchanges it for tokens.
- `get_access_token()` is used by the daily job: refreshes silently.
  Refresh tokens last ~15 days and are treated as single-use, so the newest
  one is always saved. If the job doesn't run for 15 days, run login again.
"""
import base64
import html
import json
import os
import secrets
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import simplehttp
from config import S


def _token_url():
    return f"{S.base_url}/authentication/v2/token"


def _authorize_url():
    return f"{S.base_url}/authentication/v2/authorize"


def _basic_header():
    raw = f"{S.client_id}:{S.client_secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def _post_token(data):
    r = simplehttp.post(
        _token_url(),
        data=data,
        headers={
            "Authorization": _basic_header(),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Token request failed ({r.status_code}): {r.text[:400]}")
    return r.json()


def _save(tok, previous=None):
    if previous and not tok.get("refresh_token"):
        tok["refresh_token"] = previous.get("refresh_token")
    tok["expires_at"] = time.time() + int(tok.get("expires_in", 3599)) - 120
    tok["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    S.token_file.parent.mkdir(parents=True, exist_ok=True)
    S.token_file.write_text(json.dumps(tok, indent=2), encoding="utf-8")
    try:
        os.chmod(S.token_file, 0o600)
    except OSError:
        pass
    return tok


def _load():
    if not S.token_file.exists():
        return None
    return json.loads(S.token_file.read_text(encoding="utf-8"))


def login(timeout_s=300):
    S.require_credentials()
    state = secrets.token_urlsafe(16)
    cb = urllib.parse.urlparse(S.callback_url)
    port = cb.port or 80
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" not in q and "error" not in q:
                self.send_response(404)
                self.end_headers()
                return
            result.update({k: v[0] for k, v in q.items()})
            ok = "code" in q and result.get("state") == state
            msg = ("FOMO1 login complete. You can close this tab."
                   if ok else f"Login failed: {result.get('error_description') or result.get('error') or 'state mismatch'}")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<html><body style='font-family:sans-serif;padding:40px'>"
                             f"<h3>{html.escape(msg)}</h3></body></html>".encode())

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 5
    params = {
        "response_type": "code",
        "client_id": S.client_id,
        "redirect_uri": S.callback_url,
        "scope": S.scopes,
        "state": state,
    }
    url = _authorize_url() + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    print("Opening browser for Autodesk sign-in...\nIf it doesn't open, paste this URL:\n" + url)
    webbrowser.open(url)

    deadline = time.time() + timeout_s
    while not result and time.time() < deadline:
        server.handle_request()
    server.server_close()

    if "code" not in result:
        raise SystemExit(f"Login not completed: {result.get('error_description') or result.get('error') or 'timeout'}")
    if result.get("state") != state:
        raise SystemExit("Login aborted: state mismatch (possible CSRF).")

    tok = _post_token({
        "grant_type": "authorization_code",
        "code": result["code"],
        "redirect_uri": S.callback_url,
    })
    _save(tok)
    print(f"Tokens saved to {S.token_file} (keep this file private).")
    return tok


def get_access_token(force_refresh=False):
    tok = _load()
    if not tok:
        raise SystemExit("Not logged in. Run:  python fomo1.py login")
    if not force_refresh and tok.get("expires_at", 0) > time.time():
        return tok["access_token"]
    if not tok.get("refresh_token"):
        raise SystemExit("No refresh token stored. Run:  python fomo1.py login")
    try:
        new = _post_token({
            "grant_type": "refresh_token",
            "refresh_token": tok["refresh_token"],
            "scope": S.scopes,
        })
    except RuntimeError as e:
        raise SystemExit(f"{e}\nRefresh token expired or revoked. Run:  python fomo1.py login")
    return _save(new, previous=tok)["access_token"]
