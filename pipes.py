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
    def get_sample_response(messages: list[dict[str, str]]) -> str:
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

    @staticmethod
    def generate_random_chunks(text: str, min_chunks: int = MIN_CHUNKS, max_chunks: int = MAX_CHUNKS) -> list[str]:
        num_chunks = secrets.randbelow(max_chunks - min_chunks + 1) + min_chunks

        tokens = re.findall(r"\S+|\s+", text)
        all_parts = []

        for token in tokens:
            if token.strip():
                parts = re.findall(r"\w+|[^\w\s]", token)
                all_parts.extend(parts)
                if token != tokens[-1]:
                    all_parts.append(" ")

        all_parts = [part for part in all_parts if part]

        if len(all_parts) <= num_chunks:
            return all_parts

        chunks = []
        chunk_size = len(all_parts) // num_chunks
        remainder = len(all_parts) % num_chunks

        start_idx = 0
        for i in range(num_chunks):
            current_chunk_size = chunk_size + (1 if i < remainder else 0)
            end_idx = start_idx + current_chunk_size

            chunk_content = "".join(all_parts[start_idx:end_idx])
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
        model_name = "gpt-4o-mini"
        system_fingerprint = f"fp_{uuid.uuid4().hex[:12]}"

        print(f"[DEBUG] Streaming {len(chunks)} chunks with {CHUNK_DELAY_SECONDS}s delay each")

        for i, chunk_content in enumerate(chunks):
            chunk_data = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created_timestamp,
                "model": model_name,
                "system_fingerprint": system_fingerprint,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": chunk_content},
                        "logprobs": None,
                        "finish_reason": None,
                    }
                ],
            }

            yield f"data: {json.dumps(chunk_data)}\n\n"

            if i < len(chunks) - 1:
                time.sleep(CHUNK_DELAY_SECONDS)

        final_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created_timestamp,
            "model": model_name,
            "system_fingerprint": system_fingerprint,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
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
        }

        yield f"data: {json.dumps(final_chunk)}\n\n"
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
                "prompt_tokens": sum(len(msg.get("content", "").split()) for msg in messages),
                "completion_tokens": len(response_text.split()),
                "total_tokens": sum(len(msg.get("content", "").split()) for msg in messages)
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
