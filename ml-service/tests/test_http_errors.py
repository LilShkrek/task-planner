import io

from app.main import Handler


def raise_broken_pipe(*args, **kwargs):
    raise BrokenPipeError("клиент закрыл соединение")


class BrokenWriter:
    def write(self, body):
        raise_broken_pipe(body)


def test_write_json_handles_broken_pipe_in_headers():
    handler = object.__new__(Handler)
    handler.send_response = raise_broken_pipe
    handler.send_header = lambda *args, **kwargs: None
    handler.end_headers = lambda: None
    handler.wfile = io.BytesIO()

    handler._write_json(200, {"ok": True})


def test_write_json_handles_broken_pipe_in_body():
    handler = object.__new__(Handler)
    handler.send_response = lambda *args, **kwargs: None
    handler.send_header = lambda *args, **kwargs: None
    handler.end_headers = lambda: None
    handler.wfile = BrokenWriter()

    handler._write_json(200, {"ok": True})
