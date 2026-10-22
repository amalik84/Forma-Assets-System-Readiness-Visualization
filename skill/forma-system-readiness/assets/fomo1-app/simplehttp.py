"""Tiny HTTP helper built on the Python standard library (no pip install needed).

Uses the operating-system certificate store on Windows, so it works behind
corporate HTTPS inspection proxies. Mimics the small part of `requests` FOMO1 uses.
"""
import json as _json
import urllib.error
import urllib.parse
import urllib.request


class Response:
    def __init__(self, status, headers, body, url):
        self.status_code = status
        self.headers = headers
        self.content = body
        self.url = url

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    @property
    def text(self):
        return self.content.decode("utf-8", errors="replace")

    def json(self):
        return _json.loads(self.text)


def request(method, url, params=None, data=None, json_body=None, headers=None, timeout=60):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    h = dict(headers or {})
    body = None
    if json_body is not None:
        body = _json.dumps(json_body).encode()
        h.setdefault("Content-Type", "application/json")
    elif data is not None:
        body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return Response(r.status, r.headers, r.read(), r.geturl())
    except urllib.error.HTTPError as e:
        return Response(e.code, e.headers, e.read(), url)
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error calling {url}: {e.reason}") from e


def post(url, data=None, headers=None, timeout=30):
    return request("POST", url, data=data, headers=headers, timeout=timeout)
