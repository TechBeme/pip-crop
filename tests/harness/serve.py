"""Static server with HTTP Range support (needed for <video> seeking).
Port 8765: same-origin test pages. 8766: cross-origin, NO CORS headers.
8767: cross-origin WITH Access-Control-Allow-Origin: *."""
import http.server, os, re, sys, threading
from socketserver import ThreadingMixIn

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "www")


class Handler(http.server.SimpleHTTPRequestHandler):
    cors = False

    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):
        pass

    def end_headers(self):
        if self.cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_head(self):
        path = self.translate_path(self.path.split("?")[0])
        rng = self.headers.get("Range")
        if not rng or not os.path.isfile(path):
            return super().send_head()
        m = re.match(r"bytes=(\d*)-(\d*)", rng)
        size = os.path.getsize(path)
        start = int(m.group(1)) if m.group(1) else 0
        end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        f = open(path, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        self._remaining = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        rem = getattr(self, "_remaining", None)
        if rem is None:
            return super().copyfile(source, outputfile)
        try:
            while rem > 0:
                buf = source.read(min(65536, rem))
                if not buf:
                    break
                outputfile.write(buf)
                rem -= len(buf)
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass


class CorsHandler(Handler):
    cors = True


class Server(ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    servers = [Server(("127.0.0.1", 8765), Handler), Server(("127.0.0.1", 8766), Handler),
               Server(("127.0.0.1", 8767), CorsHandler)]
    for s in servers[1:]:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    print("serving", ROOT, flush=True)
    servers[0].serve_forever()
