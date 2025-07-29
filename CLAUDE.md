# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Server-Sent Events (SSE) server that streams responses in the Langbase API format. It provides OpenAI-compatible streaming responses with proper SSE formatting and custom headers. The server uses Python's built-in HTTP server and requires Python 3.13.

## Development Commands

- `python3 main.py` - Start the server on localhost:8000
- `python3 test_server.py` - Run basic integration tests
- `python3 test_connection_behavior.py` - Test connection behavior patterns
- `uv add <package>` - Add Python dependencies (uses uv for dependency management)
- `ruff check` - Run linting checks
- `ruff format` - Format code according to project standards

## Architecture

### Core Components

The application follows a modular architecture with clear separation of concerns:

**HTTP Handler Layer** (`http_handler.py`):
- `BaseSSERequestHandler` - Base HTTP request handler with CORS support
- `SSERequestHandler` - Main request handler that delegates to business logic handlers
- Handles routing for `/v1/pipes/run`, `/v1/threads`, and health endpoints

**Business Logic Layer**:
- **Pipes Module** (`pipes.py`) - Handles streaming and non-streaming AI responses
  - `PipeResponseGenerator` - Generates sample responses based on message content
  - `SSEStreamGenerator` - Creates Server-Sent Events streams with proper OpenAI formatting
  - `PipeHandler` - Orchestrates pipe execution logic
  
- **Threads Module** (`threads.py`) - Manages conversation threads and message storage
  - `ThreadStorage` - In-memory storage for threads and messages
  - `ThreadHandler` - Business logic for thread operations (create, list, append messages)

**Main Entry Point** (`main.py`):
- Server startup and configuration
- Imports and uses `SSERequestHandler` from `http_handler.py`

### Key Patterns

- **Error Handling**: Custom exception hierarchy for different error types (`PipeError`, `ThreadError` and their subclasses)
- **Response Format**: Strict adherence to OpenAI chat completion format with Langbase-specific headers (`lb-thread-id`)
- **Stream Generation**: Text is broken into random chunks (5-10 per response) with 1-second delays between chunks
- **Memory Storage**: In-memory dictionaries for thread and message persistence (no external database)

### Configuration

Key constants in `pipes.py`:
- `CHUNK_DELAY_SECONDS = 1.0` - Delay between streaming chunks
- `MIN_CHUNKS = 5` / `MAX_CHUNKS = 10` - Range for random chunk generation
- `SAMPLE_RESPONSES` - Predefined responses triggered by message content keywords

## API Endpoints

- `POST /v1/pipes/run` - Main endpoint for AI completions (streaming/non-streaming)
- `POST /v1/threads` - Create new conversation threads
- `POST /v1/threads/{threadId}/messages` - Append messages to existing threads
- `GET /v1/threads/{threadId}/messages` - Retrieve thread messages
- `GET /health` - Health check with timestamp
- `GET /` - Basic server status

## Testing

Run `python3 test_server.py` after starting the server to validate:
- Health endpoints functionality
- Non-streaming response format
- Streaming SSE format and timing
- Chunk count and delay verification

The test suite expects the server to be running on localhost:8000 and validates proper OpenAI format compliance, custom headers, and streaming behavior.