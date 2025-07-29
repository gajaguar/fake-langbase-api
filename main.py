import contextlib
import json
import re
import secrets
import time
import uuid
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from typing import Any
from urllib.parse import urlparse

# Configuration constants
CHUNK_DELAY_SECONDS = 1.0  # Configurable delay between chunks (default: 1 second)
MIN_CHUNKS = 5  # Minimum number of chunks (configurable)
MAX_CHUNKS = 10  # Maximum number of chunks (configurable)

# Sample responses for simulation
SAMPLE_RESPONSES = [
    "Hello! I'm an AI assistant created by Langbase. How can I help you today?",
    "I understand you're looking for information. Let me provide you with a comprehensive response.",
    "Based on your question, here's what I can tell you about the topic you're interested in.",
    "Thank you for your question! I'm here to assist you with accurate and helpful information.",
]


def get_sample_response(messages: list[dict[str, str]]) -> str:
    """Generate a sample response based on the input messages."""
    if not messages:
        return SAMPLE_RESPONSES[0]

    last_message = messages[-1].get("content", "").lower()

    if "hello" in last_message or "hi" in last_message:
        return SAMPLE_RESPONSES[0]
    if "help" in last_message or "question" in last_message:
        return SAMPLE_RESPONSES[1]
    if "information" in last_message or "tell me" in last_message:
        return SAMPLE_RESPONSES[2]
    return SAMPLE_RESPONSES[3]


def generate_random_chunks(text: str, min_chunks: int = MIN_CHUNKS, max_chunks: int = MAX_CHUNKS) -> list[str]:
    """Generate a random number of chunks from the text."""
    # Determine random number of chunks
    num_chunks = secrets.randbelow(max_chunks - min_chunks + 1) + min_chunks

    # If text is shorter than desired chunks, split by words/punctuation
    tokens = re.findall(r"\S+|\s+", text)
    all_parts = []

    for token in tokens:
        if token.strip():  # Non-whitespace token
            # Further split punctuation from words
            parts = re.findall(r"\w+|[^\w\s]", token)
            all_parts.extend(parts)
            # Add space after word/punctuation (except for last token)
            if token != tokens[-1]:
                all_parts.append(" ")

    # Remove empty parts
    all_parts = [part for part in all_parts if part]

    if len(all_parts) <= num_chunks:
        # If we have fewer parts than desired chunks, return all parts
        return all_parts

    # Distribute the text across the desired number of chunks
    chunks = []
    chunk_size = len(all_parts) // num_chunks
    remainder = len(all_parts) % num_chunks

    start_idx = 0
    for i in range(num_chunks):
        # Add one extra part to some chunks to handle remainder
        current_chunk_size = chunk_size + (1 if i < remainder else 0)
        end_idx = start_idx + current_chunk_size

        # Join the parts for this chunk
        chunk_content = "".join(all_parts[start_idx:end_idx])
        if chunk_content:  # Only add non-empty chunks
            chunks.append(chunk_content)

        start_idx = end_idx

    return chunks


def generate_sse_stream(messages: list[dict[str, str]], completion_id: str, _thread_id: str):
    """Generate SSE stream in Langbase/OpenAI format with configurable timing and chunk count."""

    # Generate response text
    response_text = get_sample_response(messages)
    chunks = generate_random_chunks(response_text, MIN_CHUNKS, MAX_CHUNKS)

    # Common fields for all chunks
    created_timestamp = int(time.time())
    model_name = "gpt-4o-mini"
    system_fingerprint = f"fp_{uuid.uuid4().hex[:12]}"

    print(f"[DEBUG] Streaming {len(chunks)} chunks with {CHUNK_DELAY_SECONDS}s delay each")

    # Stream each chunk
    for i, chunk_content in enumerate(chunks):
        chunk_data = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created_timestamp,
            "model": model_name,
            "system_fingerprint": system_fingerprint,
            "choices": [{"index": 0, "delta": {"content": chunk_content}, "logprobs": None, "finish_reason": None}],
        }

        yield f"data: {json.dumps(chunk_data)}\n\n"

        # Add configurable delay to simulate real streaming
        if i < len(chunks) - 1:  # Don't delay after the last chunk
            time.sleep(CHUNK_DELAY_SECONDS)

    # Send final chunk with finish_reason and usage
    final_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created_timestamp,
        "model": model_name,
        "system_fingerprint": system_fingerprint,
        "choices": [{"index": 0, "delta": {}, "logprobs": None, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": sum(len(msg.get("content", "").split()) for msg in messages),
            "completion_tokens": len(response_text.split()),
            "total_tokens": sum(len(msg.get("content", "").split()) for msg in messages) + len(response_text.split()),
        },
    }

    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"


class SSERequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for SSE server."""

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/":
            self.send_json_response({"message": "SSE Server is running", "version": "0.1.0"})
        elif parsed_path.path == "/health":
            self.send_json_response({"status": "healthy", "timestamp": int(time.time())})
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/v1/pipes/run":
            self.handle_run_pipe()
        else:
            self.send_error(404, "Not Found")

    def handle_run_pipe(self):
        """Handle the /v1/pipes/run endpoint."""
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode("utf-8"))

            # Validate request
            messages = request_data.get("messages", [])
            if not messages:
                self.send_error(400, "Messages array cannot be empty")
                return

            stream = request_data.get("stream", False)
            thread_id = request_data.get("threadId", str(uuid.uuid4()))

            # Generate unique completion ID
            completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

            if stream:
                # Send streaming response
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Expose-Headers", "lb-thread-id")
                self.send_header("lb-thread-id", thread_id)
                self.end_headers()

                # Stream the response
                try:
                    for chunk in generate_sse_stream(messages, completion_id, thread_id):
                        try:
                            self.wfile.write(chunk.encode("utf-8"))
                            self.wfile.flush()
                        except BrokenPipeError:
                            # Client disconnected
                            break
                finally:
                    # Ensure connection is closed after streaming completes
                    with contextlib.suppress(OSError):
                        self.wfile.close()
            else:
                # Send non-streaming response
                response_text = get_sample_response(messages)
                created_timestamp = int(time.time())

                raw_response = {
                    "id": completion_id,
                    "object": "chat.completion",
                    "created": created_timestamp,
                    "model": "gpt-4o-mini",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": response_text},
                            "logprobs": None,
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": sum(len(msg.get("content", "").split()) for msg in messages),
                        "completion_tokens": len(response_text.split()),
                        "total_tokens": sum(len(msg.get("content", "").split()) for msg in messages)
                        + len(response_text.split()),
                    },
                    "system_fingerprint": f"fp_{uuid.uuid4().hex[:12]}",
                }

                response = {"completion": response_text, "raw": raw_response}

                self.send_json_response(response, extra_headers={"lb-thread-id": thread_id})

        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except (ValueError, KeyError, TypeError) as e:
            self.send_error(500, f"Internal Server Error: {e!s}")

    def send_json_response(
        self, data: dict[str, Any], status_code: int = 200, extra_headers: dict[str, str] | None = None
    ):
        """Send a JSON response."""
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
        """Override to customize logging."""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {fmt % args}")


def run_server(host="0.0.0.0", port=8000):  # noqa: S104
    """Run the SSE server."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, SSERequestHandler)

    print(f"SSE Server starting on http://{host}:{port}")
    print("Endpoints:")
    print("  GET  /           - Health check")
    print("  GET  /health     - Detailed health check")
    print("  POST /v1/pipes/run - Run pipe (streaming/non-streaming)")
    print("\nPress Ctrl+C to stop the server")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()


if __name__ == "__main__":
    run_server()
