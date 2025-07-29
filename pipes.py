import json
import re
import secrets
import time
import uuid
from typing import Any

# Configuration constants
CHUNK_DELAY_SECONDS = 1.0
MIN_CHUNKS = 5
MAX_CHUNKS = 10

# Sample responses for simulation
SAMPLE_RESPONSES = [
    "Hello! I'm an AI assistant created by Langbase. How can I help you today?",
    "I understand you're looking for information. Let me provide you with a comprehensive response.",
    "Based on your question, here's what I can tell you about the topic you're interested in.",
    "Thank you for your question! I'm here to assist you with accurate and helpful information.",
]


class PipeResponseGenerator:
    @staticmethod
    def calculate_prompt_tokens(messages: list[dict[str, str]]) -> int:
        """Calculate prompt tokens with robust error handling for different message structures."""
        prompt_tokens = 0
        for msg in messages:
            try:
                if isinstance(msg, dict):
                    content = msg.get("content", "")
                elif isinstance(msg, list) and msg:
                    # Handle nested list structure
                    first_item = msg[0]
                    if isinstance(first_item, dict):
                        content = first_item.get("content", "")
                    else:
                        content = str(first_item)
                else:
                    content = str(msg)
                prompt_tokens += len(content.split())
            except (AttributeError, KeyError, IndexError, TypeError):
                # Skip malformed messages
                continue
        return prompt_tokens

    @staticmethod
    def get_sample_response(messages: list[dict[str, str]]) -> str:
        if not messages:
            return SAMPLE_RESPONSES[0]

        # Handle potential nested structure or malformed messages
        last_message_obj = messages[-1]

        # Handle different message structures with robust error handling
        try:
            if isinstance(last_message_obj, dict):
                last_message = last_message_obj.get("content", "").lower()
            elif isinstance(last_message_obj, list) and last_message_obj:
                # If it's a list, try to get the first item
                first_item = last_message_obj[0]
                if isinstance(first_item, dict):
                    last_message = first_item.get("content", "").lower()
                else:
                    last_message = str(first_item).lower()
            else:
                # Fallback: convert to string
                last_message = str(last_message_obj).lower()
        except (KeyError, IndexError, AttributeError, TypeError):
            # If any error occurs, use fallback
            last_message = ""

        if "hello" in last_message or "hi" in last_message:
            return SAMPLE_RESPONSES[0]
        if "help" in last_message or "question" in last_message:
            return SAMPLE_RESPONSES[1]
        if "information" in last_message or "tell me" in last_message:
            return SAMPLE_RESPONSES[2]
        return SAMPLE_RESPONSES[3]

    @staticmethod
    def generate_random_chunks(text: str, min_chunks: int = MIN_CHUNKS, max_chunks: int = MAX_CHUNKS) -> list[str]:
        """Generate realistic token-level chunks similar to OpenAI's streaming format."""
        # First, tokenize the text into realistic chunks
        # Split by words, punctuation, and whitespace to simulate token-level streaming
        tokens = []

        # Split text into words and handle punctuation separately
        words = re.findall(r"\w+|[^\w\s]|\s+", text)

        for word in words:
            if word.strip():  # Non-whitespace
                if len(word) > 4 and word.isalpha():
                    # Split longer words into smaller chunks (simulating subword tokens)
                    mid = len(word) // 2
                    tokens.extend([word[:mid], word[mid:]])
                else:
                    tokens.append(word)
            else:
                # Preserve whitespace as separate tokens
                tokens.append(word)

        # Remove empty tokens
        tokens = [token for token in tokens if token]

        # If we have fewer natural tokens than desired chunks, create smaller pieces
        if len(tokens) < min_chunks:
            # Further split some tokens
            expanded_tokens = []
            for token in tokens:
                if len(token) > 2 and token.isalpha():
                    # Split into character-level chunks for very small responses
                    expanded_tokens.extend(list(token))
                else:
                    expanded_tokens.append(token)
            tokens = expanded_tokens

        # Randomly select number of chunks to return
        num_chunks = min(len(tokens), secrets.randbelow(max_chunks - min_chunks + 1) + min_chunks)

        if num_chunks >= len(tokens):
            return tokens

        # Distribute tokens across the desired number of chunks
        chunks = []
        chunk_size = len(tokens) // num_chunks
        remainder = len(tokens) % num_chunks

        start_idx = 0
        for i in range(num_chunks):
            current_chunk_size = chunk_size + (1 if i < remainder else 0)
            end_idx = start_idx + current_chunk_size

            chunk_tokens = tokens[start_idx:end_idx]
            chunk_content = "".join(chunk_tokens)

            if chunk_content:
                chunks.append(chunk_content)

            start_idx = end_idx

        return chunks


class SSEStreamGenerator:
    def __init__(self, response_generator: PipeResponseGenerator):
        self.response_generator = response_generator

    def generate_sse_stream(self, messages: list[dict[str, str]], completion_id: str, _thread_id: str):
        response_text = self.response_generator.get_sample_response(messages)
        chunks = self.response_generator.generate_random_chunks(response_text)

        created_timestamp = int(time.time())
        model_name = "gpt-4o-mini-2024-07-18"
        system_fingerprint = f"fp_{uuid.uuid4().hex[:12]}"

        print(f"[DEBUG] Streaming {len(chunks)} chunks with {CHUNK_DELAY_SECONDS}s delay each")

        # First chunk includes role
        first_chunk_data = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created_timestamp,
            "model": model_name,
            "service_tier": "default",
            "system_fingerprint": system_fingerprint,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": "", "refusal": None},
                    "logprobs": None,
                    "finish_reason": None,
                }
            ],
            "usage": None,
        }

        yield f"data: {json.dumps(first_chunk_data)}\n\n"
        time.sleep(CHUNK_DELAY_SECONDS)

        # Content chunks
        for i, chunk_content in enumerate(chunks):
            chunk_data = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created_timestamp,
                "model": model_name,
                "service_tier": "default",
                "system_fingerprint": system_fingerprint,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": chunk_content},
                        "logprobs": None,
                        "finish_reason": None,
                    }
                ],
                "usage": None,
            }

            yield f"data: {json.dumps(chunk_data)}\n\n"

            if i < len(chunks) - 1:
                time.sleep(CHUNK_DELAY_SECONDS)

        # Finish reason chunk (no content, just finish_reason)
        finish_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created_timestamp,
            "model": model_name,
            "service_tier": "default",
            "system_fingerprint": system_fingerprint,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": None,
        }

        yield f"data: {json.dumps(finish_chunk)}\n\n"

        # Final usage chunk (empty choices, includes usage)
        prompt_tokens = self.response_generator.calculate_prompt_tokens(messages)
        completion_tokens = len(response_text.split())

        usage_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created_timestamp,
            "model": model_name,
            "service_tier": "default",
            "system_fingerprint": system_fingerprint,
            "choices": [],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0},
                "completion_tokens_details": {
                    "reasoning_tokens": 0,
                    "audio_tokens": 0,
                    "accepted_prediction_tokens": 0,
                    "rejected_prediction_tokens": 0,
                },
            },
        }

        yield f"data: {json.dumps(usage_chunk)}\n\n"
        yield "data: [DONE]\n\n"


class PipeHandler:
    def __init__(self, stream_generator: SSEStreamGenerator, response_generator: PipeResponseGenerator):
        self.stream_generator = stream_generator
        self.response_generator = response_generator

    def handle_run_pipe(self, request_data: dict[str, Any]) -> tuple[Any, int, dict[str, str] | None]:
        messages = request_data.get("messages", [])
        if not messages:
            raise InvalidPipeRequestError("Messages array cannot be empty")

        stream = request_data.get("stream", False)
        thread_id = request_data.get("threadId", str(uuid.uuid4()))
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

        if stream:
            headers = {
                "lb-thread-id": thread_id,
                "Cache-Control": "no-cache",
                "Connection": "close",
                "Access-Control-Expose-Headers": "lb-thread-id",
            }

            stream_data = self.stream_generator.generate_sse_stream(messages, completion_id, thread_id)
            return stream_data, 200, headers
        response_text = self.response_generator.get_sample_response(messages)
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
                "prompt_tokens": self.response_generator.calculate_prompt_tokens(messages),
                "completion_tokens": len(response_text.split()),
                "total_tokens": self.response_generator.calculate_prompt_tokens(messages)
                + len(response_text.split()),
            },
            "system_fingerprint": f"fp_{uuid.uuid4().hex[:12]}",
        }

        response = {"completion": response_text, "raw": raw_response}
        headers = {"lb-thread-id": thread_id}

        return response, 200, headers


class PipeError(Exception):
    pass


class InvalidPipeRequestError(PipeError):
    pass


# Global instances
response_generator = PipeResponseGenerator()
stream_generator = SSEStreamGenerator(response_generator)
pipe_handler = PipeHandler(stream_generator, response_generator)
