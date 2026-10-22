"""Serve the dashboard on this computer, with a token endpoint for the live 3D viewer.

Usage: py src/serve.py            then open http://127.0.0.1:8765
       py src/serve.py --port 9000

- Listens on 127.0.0.1 only, never on the network.
- GET /api/token returns your current access token (refreshed when needed) so the viewer can
  stream the models. The token is never written into the HTML files.
- Requests whose Host header is not this computer are refused (protects against DNS rebinding),
  and no CORS headers are sent, so other websites cannot read the token.
"""

import argparse
import json
import sys
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import auth
import config

DASHBOARD = config.ROOT / "dashboard"
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}


def host_allowed(host_header, port):
    host, _, host_port = (host_header or "").rpartition(":") if ":" in (host_header or "") else (host_header, "", "")
    return host in ALLOWED_HOSTS and host_port in ("", str(port))


class Handler(SimpleHTTPRequestHandler):
    port = None

    def do_GET(self):
        if not host_allowed(self.headers.get("Host"), self.port):
            self.send_error(403, "Only http://127.0.0.1 is allowed")
            return
        if self.path.split("?")[0] == "/api/token":
            self.send_token()
            return
        super().do_GET()

    def send_token(self):
        try:
            token = auth.get_access_token()
            tokens = json.loads(config.TOKEN_FILE.read_text(encoding="utf-8"))
            body = {"access_token": token, "expires_in": max(60, int(tokens["expires_at"] - time.time()))}
            status = 200
        except auth.AuthError as e:
            body, status = {"error": str(e).splitlines()[0]}, 401
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        if "/api/token" not in (args[0] if args else ""):
            sys.stderr.write("%s\n" % (fmt % args))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8765)
    port = parser.parse_args().port
    if not (DASHBOARD / "index.html").exists():
        raise SystemExit("dashboard/index.html not found. Run py src/render.py first.")
    Handler.port = port
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(DASHBOARD)))
    print(f"Dashboard on http://127.0.0.1:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
