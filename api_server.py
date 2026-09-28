import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from solution_api import build_solution_graph

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"


class GraphHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/graph":
            params = parse_qs(parsed.query)
            solution_id = params.get("solution", ["1"])[0]
            text = params.get("text", [""])[0]

            try:
                payload = build_solution_graph(int(solution_id), text)
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:  # pragma: no cover
                body = json.dumps({"error": str(exc)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return

        normalized_path = parsed.path or "/index.html"
        if normalized_path == "/":
            normalized_path = "/index.html"

        file_path = (DOCS_DIR / normalized_path.lstrip("/")).resolve()
        try:
            file_path.relative_to(DOCS_DIR.resolve())
        except ValueError:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return

        if not file_path.exists() or not file_path.is_file():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        content_type = "text/html"
        if file_path.suffix == ".css":
            content_type = "text/css"
        elif file_path.suffix == ".js":
            content_type = "application/javascript"
        elif file_path.suffix == ".json":
            content_type = "application/json"

        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8001"))
    server = ThreadingHTTPServer(("0.0.0.0", port), GraphHandler)
    print(f"Web app and API running on http://0.0.0.0:{port}")
    server.serve_forever()
