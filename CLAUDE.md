# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SSE Server is a Server-Sent Events implementation that streams responses in Langbase API format withOpenAI-compatible structure. The server provides both streaming and non-streaming responses with proper SSE formatting and custom headers.

## Build & Development Commands

**Start the server:**
```bash
python3 main.py
```

**Run tests:**
```bash
python3 test_server.py
python3 test_connection_behavior.py
```

**Code quality checks:**
```bash
ruff check .
ruff format .
```

## Architecture Overview

The project follows SOLID principles with clear separation of concerns:

### Core Modules

- **`main.py`** - Server entry point using Python's built-in HTTPServer
- **`http_handler.py`** - HTTP request routing and response handling with CORS support
- **`pipes.py`** - SSE streaming logic, response generation, and OpenAI format compliance
- **`threads.py`** - Thread management with in-memory storage for conversation persistence

### Key Design Patterns

- **Dependency Inversion**: High-level modules depend on abstractions, not concretions
- **Single Responsibility**: Each module has focused functionality
- **Interface Segregation**: Clean separation between HTTP handling and business logic
- **Command Pattern**: Handler classes process specific request types

### Request Flow

1. `main.py` starts HTTPServer with `SSERequestHandler`
2. `http_handler.py` routes requests and handles CORS
3. `pipes.py` generates streaming responses with configurable chunking
4. `threads.py` manages conversation state and message persistence

## API Endpoints

### Core Endpoints
- `POST /v1/pipes/run` - Main streaming/non-streaming endpoint
- `POST /v1/threads` - Create conversation thread
- `POST /v1/threads/{threadId}/messages` - Append messages to thread
- `GET /v1/threads/{threadId}/messages` - Retrieve thread messages
- `GET /health` - Health check with timestamp

### Response Format
Follows OpenAI chat completion chunk structure with:
- Custom `lb-thread-id` header (UUID v4)
- Streaming: `text/event-stream` with `data: ` prefixed chunks
- Non-streaming: Standard JSON response with completion object

## Configuration

**Stream timing (pipes.py:8-11):**
```python
CHUNK_DELAY_SECONDS = 1.0  # Delay between chunks
MIN_CHUNKS = 5            # Minimum chunks per response
MAX_CHUNKS = 10           # Maximum chunks per response  
```

**Response samples (pipes.py:14-19):**
Modify `SAMPLE_RESPONSES` array for different simulated AI responses.

## Technology Stack

- **Runtime**: Python 3.13+ (built-in libraries only for server)
- **Optional Dependencies**: FastAPI, Uvicorn (in pyproject.toml but not used)
- **Code Quality**: Ruff (linting and formatting)
- **Architecture**: Pure Python HTTP server with custom request handlers

## Testing Strategy

- **`test_server.py`** - Functional tests for all endpoints, streaming behavior, and timing
- **`test_connection_behavior.py`** - Connection lifecycle and proper stream termination
- Tests use Python's urllib for HTTP requests and raw sockets for connection testing
- Validates OpenAI format compliance, chunk timing, and SSE protocol adherence

## Development Notes

- Server uses in-memory storage for threads (data lost on restart)
- Streaming responses simulate AI generation with random chunking
- Connection handling includes proper cleanup for broken pipes
- CORS enabled for web application integration