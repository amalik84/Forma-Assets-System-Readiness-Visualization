"""APS 3-legged OAuth v2: login once in the browser, then refresh unattended.

Usage:
    py src/auth.py login     open the browser, sign in, store tokens
    py src/auth.py refresh   get a new access token with the stored refresh token
    py src/auth.py status    show whether we are logged in (never prints tokens)

Other modules call get_access_token().
"""

import base64
import json
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import config

AUTHORIZE_URL = f"{config.BASE_URL}/authentication/v2/authorize"
TOKEN_URL = f"{config.BASE_URL}/authentication/v2/token"
LOGIN_TIMEOUT_SECONDS = 300
REFRESH_MARGIN_SECONDS = 300


class AuthError(Exception):
    pass


# ---------- token storage ----------

def _save_tokens(payload):
    """Save straight away: APS refresh tokens are single use."""
    data = {
        "access_token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
        "expires_at": int(time.time()) + int(payload.get("expires_in", 3600)),
        "saved_at": int(time.time()),
    }
    config.TOKEN_FILE.parent.mkdir(exist_ok=True)
    tmp = config.TOKEN_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    tmp.replace(config.TOKEN_FILE)
    return data


def _load_tokens():
    if not config.TOKEN_FILE.exists():
        raise AuthError("Not logged in. Run: py src/auth.py login")
    return json.loads(config.TOKEN_FILE.read_text(encoding="utf-8"))


# ---------- token endpoint ----------

def _post_token(form):
    basic = base64.b64encode(f"{config.CLIENT_ID}:{config.CLIENT_SECRET}".encode()).decode()
    request = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(form).encode(),
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        # The error body holds a code and message, no secrets.
        detail = e.read().decode(errors="replace")[:300]
        raise AuthError(f"Token request failed ({e.code}): {detail}") from None


def refresh():
    tokens = _load_tokens()
    payload = _post_token({
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "scope": config.SCOPES,
    })
    return _save_tokens(payload)


def get_access_token():
    """Return a valid access token, refreshing it if it expires soon."""
    tokens = _load_tokens()
    if tokens["expires_at"] - time.time() < REFRESH_MARGIN_SECONDS:
        try:
            tokens = refresh()
        except AuthError as e:
            raise AuthError(f"{e}\nRe-login needed: py src/auth.py login") from None
    return tokens["access_token"]


# ---------- interactive login ----------

def login():
    callback = urllib.parse.urlparse(config.CALLBACK_URL)
    if callback.hostname not in ("localhost", "127.0.0.1"):
        raise AuthError("APS_CALLBACK_URL must point to localhost for this login helper.")
    port = callback.port or 80
    expected_path = callback.path or "/"
    state = secrets.token_urlsafe(16)
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != expected_path:
                self.send_response(404)
                self.end_headers()
                return
            query = urllib.parse.parse_qs(parsed.query)
            result["code"] = query.get("code", [None])[0]
            result["state"] = query.get("state", [None])[0]
            result["error"] = query.get("error_description", query.get("error", [None]))[0]
            ok = result["code"] and result["state"] == state
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            message = "Logged in. You can close this tab." if ok else "Login failed. Check the terminal."
            self.wfile.write(f"<html><body style='font-family:sans-serif'><h3>{message}</h3></body></html>".encode())

        def log_message(self, *args):
            pass  # keep the code out of the console

    url = AUTHORIZE_URL + "?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": config.CLIENT_ID,
        "redirect_uri": config.CALLBACK_URL,
        "scope": config.SCOPES,
        "state": state,
    })

    server = HTTPServer((callback.hostname, port), Handler)
    server.timeout = LOGIN_TIMEOUT_SECONDS
    print("Opening the browser to sign in with your Autodesk account...")
    print(f"If it does not open, paste this URL into your browser:\n{url}\n")
    webbrowser.open(url)
    server.handle_request()  # wait for one callback (or time out)
    server.server_close()

    if not result:
        raise AuthError("No callback received within 5 minutes.")
    if result.get("error"):
        raise AuthError(f"Login refused: {result['error']}")
    if result.get("state") != state:
        raise AuthError("State mismatch, login aborted.")

    payload = _post_token({
        "grant_type": "authorization_code",
        "code": result["code"],
        "redirect_uri": config.CALLBACK_URL,
    })
    _save_tokens(payload)
    print("Logged in. Tokens saved to .tokens/token.json")


def status():
    try:
        tokens = _load_tokens()
    except AuthError as e:
        print(e)
        return
    left = int(tokens["expires_at"] - time.time())
    saved = time.strftime("%Y-%m-%d %H:%M", time.localtime(tokens["saved_at"]))
    state = f"valid for {left // 60} more minutes" if left > 0 else "expired (will refresh on next call)"
    print(f"Logged in. Access token {state}. Tokens last saved {saved}.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    try:
        if command == "login":
            login()
        elif command == "refresh":
            refresh()
            print("Refreshed. New tokens saved.")
        elif command == "status":
            status()
        else:
            print(__doc__)
            sys.exit(2)
    except AuthError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
