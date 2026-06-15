import cgi
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from analyzer import analyze_uploaded_point, analyze_video_full, build_prediction_summary, dependency_status, summarize_route
from sample_data import get_preset_route
from video_preview import mjpeg_frames, resolve_media_path


HOST = "127.0.0.1"
PORT = 8099
ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = ROOT / "uploads"


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "ZhixingHubBackend/0.1"

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self.write_json({"ok": True, "service": "zhixing-hub-backend"})
            return
        if path == "/api/preset-route":
            self.write_json(get_preset_route())
            return
        if path == "/api/dependencies":
            self.write_json(dependency_status())
            return
        if path.startswith("/media/"):
            self.serve_media(path)
            return
        if path.startswith("/preview/"):
            self.serve_preview(path)
            return
        self.serve_static(path)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/predict":
            payload = self.read_json()
            route = summarize_route(payload.get("route", payload))
            self.write_json(build_prediction_summary(route))
            return
        if path == "/api/upload":
            self.handle_upload()
            return
        if path == "/api/analyze-video":
            self.handle_analyze_video()
            return
        self.write_json({"error": "Not found"}, status=404)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def handle_upload(self):
        content_type = self.headers.get("Content-Type", "")
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
            },
        )

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        files = form["files"] if "files" in form else []
        if not isinstance(files, list):
            files = [files]

        points = []
        saved = []
        for index, item in enumerate(files):
            if not getattr(item, "filename", None):
                continue
            filename = Path(item.filename).name
            target = UPLOAD_DIR / filename
            with target.open("wb") as out:
                out.write(item.file.read())
            saved.append(str(target))
            points.append(analyze_uploaded_point(filename, index))

        self.write_json({"saved": saved, "points": points})

    def handle_analyze_video(self):
        payload = self.read_json()
        filename = Path(payload.get("filename", "")).name
        index = int(payload.get("index", 0) or 0)
        if not filename:
            self.write_json({"ok": False, "error": "filename is required"}, status=400)
            return
        target = UPLOAD_DIR / filename
        if not target.exists():
            self.write_json({"ok": False, "error": "uploaded file not found"}, status=404)
            return
        self.write_json(analyze_video_full(target, index))

    def write_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_static(self, path):
        if path == "/":
            relative = "index.html"
        else:
            relative = unquote(path.lstrip("/"))

        target = (ROOT / relative).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            self.write_json({"error": "Forbidden"}, status=403)
            return

        if not target.exists() or not target.is_file():
            self.write_json({"error": "Not found"}, status=404)
            return

        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_media(self, path):
        relative = unquote(path[len("/media/") :])
        target = resolve_media_path(ROOT, UPLOAD_DIR, relative)

        if target is None or not target.exists() or not target.is_file():
            self.write_json({"error": "Media not found"}, status=404)
            return

        size = target.stat().st_size
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        range_header = self.headers.get("Range")

        if range_header:
            start, end = self.parse_range(range_header, size)
            with target.open("rb") as media:
                media.seek(start)
                data = media.read(end - start + 1)
            self.send_response(206)
            self.send_header("Content-Type", content_type)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_preview(self, path):
        relative = unquote(path[len("/preview/") :])
        target = resolve_media_path(ROOT, UPLOAD_DIR, relative)
        if target is None or not target.exists() or not target.is_file():
            self.write_json({"error": "Preview media not found"}, status=404)
            return

        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            for chunk in mjpeg_frames(target):
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def parse_range(self, range_header, size):
        unit, _, value = range_header.partition("=")
        if unit != "bytes":
            return 0, size - 1
        start_text, _, end_text = value.partition("-")
        start = int(start_text) if start_text else 0
        end = int(end_text) if end_text else size - 1
        start = max(0, min(start, size - 1))
        end = max(start, min(end, size - 1))
        return start, end

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


def run():
    server = ThreadingHTTPServer((HOST, PORT), ApiHandler)
    print(f"Zhixing Hub backend running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run()
