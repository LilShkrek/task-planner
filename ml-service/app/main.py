from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os

from app.pipeline import analyze_task


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._write_json(200, {"status": "ok"})
            return
        self._write_json(404, {"error": "маршрут не найден"})

    def do_POST(self):
        if self.path != "/analyze":
            self._write_json(404, {"error": "маршрут не найден"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            self._write_json(400, {"error": "некорректный JSON"})
            return

        try:
            result = analyze_task(payload)
        except Exception as exc:
            self._write_json(500, {"error": str(exc)})
            return

        self._write_json(200, result)

    def log_message(self, fmt, *args):
        return

    def _write_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            print("клиент закрыл соединение до отправки ответа ML service", flush=True)


def main():
    host = os.getenv("ML_SERVICE_ADDR", "0.0.0.0")
    port = int(os.getenv("ML_SERVICE_PORT", "8090"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ML service запущен на {host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
