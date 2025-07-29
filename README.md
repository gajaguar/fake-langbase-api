# SSE Server

A Server-Sent Events (SSE) server that streams responses in the exact Langbase API format. This server provides OpenAI-compatible streaming responses with proper SSE formatting and custom headers.

## Features

- **Langbase API Compatible**: Streams responses in the exact format specified by Langbase API documentation
- **OpenAI Format**: Uses OpenAI chat completion chunk structure
- **Custom Headers**: Includes `lb-thread-id` header with UUID v4 values
- **Chunked Streaming**: Breaks responses into individual words/punctuation for realistic streaming
- **Dual Mode**: Supports both streaming and non-streaming responses
- **CORS Enabled**: Ready for web application integration

## Installation

This server uses only Python's built-in libraries, so no additional dependencies are required.

Run the server:
```bash
python3 main.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### POST /v1/pipes/run

Main endpoint that mimics the Langbase Pipe Run API.

**Request Body:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hello!"
    }
  ],
  "stream": true
}
```

**Parameters:**
- `messages` (required): Array of message objects with `role` and `content`
- `stream` (optional): Boolean to enable streaming mode (default: false)
- `variables` (optional): Object with pipe variables
- `threadId` (optional): Thread ID for conversation continuation

**Response Headers (Streaming):**
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `lb-thread-id: <UUID v4>`

**Streaming Response Format:**
```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1719848588,"model":"gpt-4o-mini","system_fingerprint":"fp_44709d6fcb","choices":[{"index":0,"delta":{"content":"Hello"},"logprobs":null,"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1719848588,"model":"gpt-4o-mini","system_fingerprint":"fp_44709d6fcb","choices":[{"index":0,"delta":{"content":" there"},"logprobs":null,"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1719848588,"model":"gpt-4o-mini","system_fingerprint":"fp_44709d6fcb","choices":[{"index":0,"delta":{},"logprobs":null,"finish_reason":"stop"}],"usage":{"prompt_tokens":2,"completion_tokens":4,"total_tokens":6}}

data: [DONE]
```

### GET /

Health check endpoint that returns server status.

### GET /health

Detailed health check with timestamp.

## Testing

### Using curl (Streaming)

```bash
curl -X POST http://localhost:8000/v1/pipes/run \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Hello!"
      }
    ],
    "stream": true
  }'
```

### Using curl (Non-streaming)

```bash
curl -X POST http://localhost:8000/v1/pipes/run \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Hello!"
      }
    ],
    "stream": false
  }'
```

### Using JavaScript (Browser)

```javascript
const response = await fetch('http://localhost:8000/v1/pipes/run', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    messages: [
      {
        role: 'user',
        content: 'Hello!'
      }
    ],
    stream: true
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      if (data === '[DONE]') {
        console.log('Stream finished');
        break;
      }
      try {
        const parsed = JSON.parse(data);
        console.log('Chunk:', parsed);
      } catch (e) {
        // Skip invalid JSON
      }
    }
  }
}
```

## Response Format Details

The server follows the exact Langbase API streaming format:

1. **Each chunk** is prefixed with `data: ` and followed by `\n\n`
2. **JSON structure** matches OpenAI chat completion chunks
3. **Custom header** `lb-thread-id` contains a UUID v4
4. **Final chunk** includes usage information and `finish_reason: "stop"`
5. **Stream ends** with `data: [DONE]\n\n`

## Development

The server includes sample responses and simulates AI-generated content by chunking predefined text. To customize responses, modify the `SAMPLE_RESPONSES` array and `get_sample_response()` function in `main.py`.

## License

MIT License