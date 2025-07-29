import asyncio
import json
import time
import uuid
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
from typing import List, Dict, Any, Optional





# Sample responses for simulation
SAMPLE_RESPONSES = [
    "Hello! I'm an AI assistant created by Langbase. How can I help you today?",
    "I understand you're looking for information. Let me provide you with a comprehensive response.",
    "Based on your question, here's what I can tell you about the topic you're interested in.",
    "Thank you for your question! I'm here to assist you with accurate and helpful information.",
]


def get_sample_response(messages: List[Dict[str, str]]) -> str:
    """Generate a sample response based on the input messages."""
    if not messages:
        return SAMPLE_RESPONSES[0]

    last_message = messages[-1].get("content", "").lower()

    if "hello" in last_message or "hi" in last_message:
        return SAMPLE_RESPONSES[0]
    elif "help" in last_message or "question" in last_message:
        return SAMPLE_RESPONSES[1]
    elif "information" in last_message or "tell me" in last_message:
        return SAMPLE_RESPONSES[2]
    else:
        return SAMPLE_RESPONSES[3]


def split_into_chunks(text: str) -> List[str]:
    """Split text into individual words and punctuation for streaming."""
    # Split on whitespace but keep punctuation separate
    tokens = re.findall(r'\S+|\s+', text)
    chunks = []

    for token in tokens:
        if token.strip():  # Non-whitespace token
            # Further split punctuation from words
            parts = re.findall(r'\w+|[^\w\s]', token)
            for part in parts:
                chunks.append(part)
            # Add space after word/punctuation (except for last token)
            if token != tokens[-1]:
                chunks.append(" ")

    return [chunk for chunk in chunks if chunk]


def generate_sse_stream(messages: List[Dict[str, str]], completion_id: str, thread_id: str):
    """Generate SSE stream in Langbase/OpenAI format."""

    # Generate response text
    response_text = get_sample_response(messages)
    chunks = split_into_chunks(response_text)

    # Common fields for all chunks
    created_timestamp = int(time.time())
    model_name = "gpt-4o-mini"
    system_fingerprint = f"fp_{uuid.uuid4().hex[:12]}"

    # Stream each chunk
    for i, chunk_content in enumerate(chunks):
        chunk_data = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created_timestamp,
            "model": model_name,
            "system_fingerprint": system_fingerprint,
            "choices": [{
                "index": 0,
                "delta": {"content": chunk_content},
                "logprobs": None,
                "finish_reason": None
            }]
        }

        yield f"data: {json.dumps(chunk_data)}\n\n"

        # Add small delay to simulate real streaming
        time.sleep(0.05)

    # Send final chunk with finish_reason and usage
    final_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created_timestamp,
        "model": model_name,
        "system_fingerprint": system_fingerprint,
        "choices": [{
            "index": 0,
            "delta": {},
            "logprobs": None,
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": sum(len(msg.get("content", "").split()) for msg in messages),
            "completion_tokens": len(response_text.split()),
            "total_tokens": sum(len(msg.get("content", "").split()) for msg in messages) + len(response_text.split())
        }
    }

    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"


class SSERequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for SSE server."""

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/':
            self.send_json_response({"message": "SSE Server is running", "version": "0.1.0"})
        elif parsed_path.path == '/health':
            self.send_json_response({"status": "healthy", "timestamp": int(time.time())})
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/v1/pipes/run':
            self.handle_run_pipe()
        else:
            self.send_error(404, "Not Found")

    def handle_run_pipe(self):
        """Handle the /v1/pipes/run endpoint."""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))

            # Validate request
            messages = request_data.get('messages', [])
            if not messages:
                self.send_error(400, "Messages array cannot be empty")
                return

            stream = request_data.get('stream', False)
            thread_id = request_data.get('threadId', str(uuid.uuid4()))

            # Generate unique completion ID
            completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

            if stream:
                # Send streaming response
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Expose-Headers', 'lb-thread-id')
                self.send_header('lb-thread-id', thread_id)
                self.end_headers()

                # Stream the response
                for chunk in generate_sse_stream(messages, completion_id, thread_id):
                    try:
                        self.wfile.write(chunk.encode('utf-8'))
                        self.wfile.flush()
                    except BrokenPipeError:
                        # Client disconnected
                        break
            else:
                # Send non-streaming response
                response_text = get_sample_response(messages)
                created_timestamp = int(time.time())

                raw_response = {
                    "id": completion_id,
                    "object": "chat.completion",
                    "created": created_timestamp,
                    "model": "gpt-4o-mini",
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response_text
                        },
                        "logprobs": None,
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": sum(len(msg.get("content", "").split()) for msg in messages),
                        "completion_tokens": len(response_text.split()),
                        "total_tokens": sum(len(msg.get("content", "").split()) for msg in messages) + len(response_text.split())
                    },
                    "system_fingerprint": f"fp_{uuid.uuid4().hex[:12]}"
                }

                response = {
                    "completion": response_text,
                    "raw": raw_response
                }

                self.send_json_response(response, extra_headers={'lb-thread-id': thread_id})

        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")

    def send_json_response(self, data: Dict[str, Any], status_code: int = 200, extra_headers: Dict[str, str] = None):
        """Send a JSON response."""
        response_json = json.dumps(data)

        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')

        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)

        self.end_headers()
        self.wfile.write(response_json.encode('utf-8'))

    def log_message(self, format, *args):
        """Override to customize logging."""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")


def run_server(host='0.0.0.0', port=8000):
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
