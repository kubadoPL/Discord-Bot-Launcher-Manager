"""Tiny WSGI reverse proxy: forwards /StreamerApi/* to the streaming engine
running in its own process on the same dyno (see start_web.sh).

Why: the Icecast feed loop used to share one Python interpreter (and GIL)
with all HTTP handlers of the web app. Under request load the audio thread
had to queue behind JSON work and the stream stuttered. In a separate process
it only competes with its own small API.

Everything is passed through unchanged: method, path, query string, body,
request headers (minus hop-by-hop), response status/headers/body, including
gzip (Content-Encoding) produced by the engine and its CORS headers.
"""
import http.client
import urllib.parse

_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}


class StreamerProxy:
    def __init__(self, upstream, timeout=300, chunk_size=64 * 1024):
        u = urllib.parse.urlsplit(upstream)
        if u.scheme not in ("http", "") or not u.hostname:
            raise ValueError(f"StreamerProxy needs an http://host:port upstream, got {upstream!r}")
        self.host = u.hostname
        self.port = u.port or 80
        self.prefix = u.path.rstrip("/")
        self.timeout = timeout
        self.chunk_size = chunk_size

    # ── WSGI entry point ────────────────────────────────────────────────
    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = self.prefix + urllib.parse.quote(environ.get("PATH_INFO", "") or "/", safe="/%:@&=+$,;~")
        qs = environ.get("QUERY_STRING", "")
        target = path + ("?" + qs if qs else "")

        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                name = key[5:].replace("_", "-").title()
                if name.lower() in _HOP_BY_HOP or name.lower() == "host":
                    continue
                headers[name] = value
        if environ.get("CONTENT_TYPE"):
            headers["Content-Type"] = environ["CONTENT_TYPE"]

        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            length = 0
        body = environ["wsgi.input"].read(length) if length > 0 else b""
        headers["Content-Length"] = str(len(body))
        headers["Host"] = f"{self.host}:{self.port}"

        # Let the engine see the real client / scheme / public prefix
        remote = environ.get("HTTP_X_FORWARDED_FOR") or environ.get("REMOTE_ADDR", "")
        if remote:
            headers["X-Forwarded-For"] = remote
        headers["X-Forwarded-Proto"] = environ.get("HTTP_X_FORWARDED_PROTO") or environ.get("wsgi.url_scheme", "http")
        headers["X-Forwarded-Host"] = environ.get("HTTP_HOST", "")
        headers["X-Forwarded-Prefix"] = environ.get("SCRIPT_NAME", "")

        conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            conn.request(method, target, body=body, headers=headers)
            resp = conn.getresponse()
        except Exception as e:  # engine down / starting up
            conn.close()
            payload = b'{"error":"streamer engine unavailable"}'
            start_response("502 Bad Gateway", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(payload))),
                ("Access-Control-Allow-Origin", "*"),
                ("X-Proxy-Error", str(e)[:120]),
            ])
            return [payload]

        status = f"{resp.status} {resp.reason}"
        out_headers = [(k, v) for k, v in resp.getheaders() if k.lower() not in _HOP_BY_HOP]
        start_response(status, out_headers)
        if method == "HEAD" or resp.status in (204, 304):
            resp.read()
            conn.close()
            return [b""]
        return self._stream(resp, conn)

    def _stream(self, resp, conn):
        try:
            while True:
                chunk = resp.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            conn.close()
