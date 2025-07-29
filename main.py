from http.server import HTTPServer

from http_handler import SSERequestHandler


def run_server(host="0.0.0.0", port=8000):  # noqa: S104
    server_address = (host, port)
    httpd = HTTPServer(server_address, SSERequestHandler)

    print(f"SSE Server starting on http://{host}:{port}")
    print("Endpoints:")
    print("  GET  /           - Health check")
    print("  GET  /health     - Detailed health check")
    print("  POST /v1/pipes/run - Run pipe (streaming/non-streaming)")
    print("  POST /v1/threads - Create thread")
    print("  POST /v1/threads/{threadId}/messages - Append messages")
    print("  GET  /v1/threads/{threadId}/messages - List messages")
    print("\nPress Ctrl+C to stop the server")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()


if __name__ == "__main__":
    run_server()
