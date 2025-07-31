import contextlib
import json
import time
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse

from pipes import InvalidPipeRequestError
from pipes import pipe_handler
from threads import InvalidRequestError
from threads import ThreadConflictError
from threads import ThreadNotFoundError
from threads import thread_handler

MIN_PATH_PARTS = 4


class BaseSSERequestHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/":
            self.send_json_response({"message": "SSE Server is running", "version": "0.1.0"})
        elif parsed_path.path == "/health":
            self.send_json_response({"status": "healthy", "timestamp": int(time.time())})
        elif parsed_path.path.startswith("/v1/threads/") and parsed_path.path.endswith("/messages"):
            self._handle_list_messages()
        elif parsed_path.path.startswith("/v1/threads/") and not parsed_path.path.endswith("/messages"):
            # GET /v1/threads/{threadId} - Get thread
            self._handle_get_thread()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/v1/pipes/run":
            self._handle_run_pipe()
        elif parsed_path.path == "/v1/threads":
            self._handle_create_thread()
        elif parsed_path.path.startswith("/v1/threads/") and parsed_path.path.endswith("/messages"):
            self._handle_append_messages()
        elif parsed_path.path.startswith("/v1/threads/") and not parsed_path.path.endswith("/messages"):
            # POST /v1/threads/{threadId} - Update thread
            self._handle_update_thread()
        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path.startswith("/v1/threads/") and not parsed_path.path.endswith("/messages"):
            # DELETE /v1/threads/{threadId} - Delete thread
            self._handle_delete_thread()
        else:
            self.send_error(404, "Not Found")

    def _handle_run_pipe(self):
        try:
            request_data = self._parse_request_body()
            result, status_code, headers = pipe_handler.handle_run_pipe(request_data)

            if headers and "Cache-Control" in headers:
                # Streaming response
                self.send_response(status_code)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Access-Control-Allow-Origin", "*")
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()

                try:
                    for chunk in result:
                        try:
                            self.wfile.write(chunk.encode("utf-8"))
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                            # Client disconnected - this is normal behavior
                            break
                finally:
                    with contextlib.suppress(OSError):
                        self.wfile.close()
            else:
                # Non-streaming response
                self.send_json_response(result, status_code, headers)

        except InvalidPipeRequestError as e:
            self.send_error(400, str(e))
        except (ValueError, KeyError, TypeError) as e:
            self.send_error(500, f"Internal Server Error: {e!s}")

    def _handle_create_thread(self):
        try:
            request_data = self._parse_request_body(allow_empty=True)
            result, status_code = thread_handler.handle_create_thread(request_data)
            self.send_json_response(result, status_code)

        except ThreadConflictError as e:
            self.send_error(409, str(e))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except (ValueError, KeyError, TypeError) as e:
            self.send_error(500, f"Internal Server Error: {e!s}")

    def _handle_append_messages(self):
        try:
            thread_id = self._extract_thread_id()
            request_data = self._parse_request_body()
            result, status_code = thread_handler.handle_append_messages(thread_id, request_data)
            self.send_json_response(result, status_code)

        except ThreadNotFoundError:
            self.send_error(404, "Thread not found")
        except InvalidRequestError as e:
            self.send_error(400, str(e))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except (ValueError, KeyError, TypeError) as e:
            self.send_error(500, f"Internal Server Error: {e!s}")

    def _handle_list_messages(self):
        try:
            thread_id = self._extract_thread_id()
            result, status_code = thread_handler.handle_list_messages(thread_id)
            self.send_json_response(result, status_code)

        except ThreadNotFoundError:
            self.send_error(404, "Thread not found")
        except (ValueError, KeyError, TypeError) as e:
            self.send_error(500, f"Internal Server Error: {e!s}")

    def _handle_get_thread(self):
        try:
            thread_id = self._extract_thread_id()
            result, status_code = thread_handler.handle_get_thread(thread_id)
            self.send_json_response(result, status_code)

        except ThreadNotFoundError:
            self.send_error(404, "Thread not found")
        except (ValueError, KeyError, TypeError) as e:
            self.send_error(500, f"Internal Server Error: {e!s}")

    def _handle_update_thread(self):
        try:
            thread_id = self._extract_thread_id()
            request_data = self._parse_request_body()
            result, status_code = thread_handler.handle_update_thread(thread_id, request_data)
            self.send_json_response(result, status_code)

        except ThreadNotFoundError:
            self.send_error(404, "Thread not found")
        except InvalidRequestError as e:
            self.send_error(400, str(e))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except (ValueError, KeyError, TypeError) as e:
            self.send_error(500, f"Internal Server Error: {e!s}")

    def _handle_delete_thread(self):
        try:
            thread_id = self._extract_thread_id()
            result, status_code = thread_handler.handle_delete_thread(thread_id)
            self.send_json_response(result, status_code)

        except ThreadNotFoundError:
            self.send_error(404, "Thread not found")
        except (ValueError, KeyError, TypeError) as e:
            self.send_error(500, f"Internal Server Error: {e!s}")

    def _extract_thread_id(self) -> str:
        path_parts = self.path.split("/")
        if len(path_parts) < MIN_PATH_PARTS:
            msg = "Invalid thread ID"
            raise ValueError(msg)
        return path_parts[3]

    def _parse_request_body(self, allow_empty: bool = False) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0 and not allow_empty:
            msg = "Request body is required"
            raise ValueError(msg)

        if content_length == 0:
            return {}

        post_data = self.rfile.read(content_length)
        return json.loads(post_data.decode("utf-8"))

    def send_json_response(
        self,
        data: dict[str, Any] | list[dict[str, Any]],
        status_code: int = 200,
        extra_headers: dict[str, str] | None = None,
    ):
        response_json = json.dumps(data)

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")

        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)

        self.end_headers()
        self.wfile.write(response_json.encode("utf-8"))

    def log_message(self, fmt, *args):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {fmt % args}")

    def handle_one_request(self):
        """Handle a single HTTP request with improved error handling for client disconnections."""
        try:
            super().handle_one_request()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            # Client disconnected - this is normal for streaming requests
            pass
        except ValueError as e:
            if "I/O operation on closed file" in str(e):
                # Client disconnected during response - this is normal
                pass
            else:
                # Re-raise other ValueError exceptions
                raise


class SSERequestHandler(BaseSSERequestHandler):
    pass
