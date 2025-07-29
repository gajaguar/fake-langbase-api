import time
import uuid
from typing import Any


class ThreadStorage:
    def __init__(self):
        self._threads = {}
        self._messages = {}

    def create_thread(self, thread_id: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if thread_id is None:
            thread_id = f"thread_{uuid.uuid4().hex}"

        if thread_id in self._threads:
            raise ThreadExistsError(f"Thread {thread_id} already exists")

        thread_data = {
            "id": thread_id,
            "object": "thread",
            "created_at": int(time.time()),
            "metadata": metadata or {},
        }

        self._threads[thread_id] = thread_data
        self._messages[thread_id] = []

        return thread_data

    def thread_exists(self, thread_id: str) -> bool:
        return thread_id in self._threads

    def get_thread(self, thread_id: str) -> dict[str, Any]:
        if thread_id not in self._threads:
            raise ThreadNotFoundError(f"Thread {thread_id} not found")
        return self._threads[thread_id]

    def add_messages(self, thread_id: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if thread_id not in self._threads:
            raise ThreadNotFoundError(f"Thread {thread_id} not found")

        created_messages = []
        for msg in messages:
            message_id = f"msg_{uuid.uuid4().hex}"
            message_data = self._create_message_data(message_id, thread_id, msg)
            self._messages[thread_id].append(message_data)
            created_messages.append(message_data)

        return created_messages

    def get_messages(self, thread_id: str) -> list[dict[str, Any]]:
        if thread_id not in self._threads:
            raise ThreadNotFoundError(f"Thread {thread_id} not found")
        return self._messages.get(thread_id, [])

    def _create_message_data(self, message_id: str, thread_id: str, message_dict: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": message_id,
            "thread_id": thread_id,
            "created_at": int(time.time()),
            "role": message_dict.get("role"),
            "content": message_dict.get("content"),
            "tool_call_id": message_dict.get("tool_call_id"),
            "tool_calls": message_dict.get("tool_calls", []),
            "name": message_dict.get("name"),
            "attachments": message_dict.get("attachments", []),
            "metadata": message_dict.get("metadata", {}),
        }


class ThreadHandler:
    def __init__(self, storage: ThreadStorage):
        self.storage = storage

    def handle_create_thread(self, request_data: dict[str, Any]) -> tuple[dict[str, Any], int]:
        try:
            thread_id = request_data.get("threadId")
            metadata = request_data.get("metadata", {})

            thread_data = self.storage.create_thread(thread_id, metadata)

            # Process initial messages if provided
            initial_messages = request_data.get("messages", [])
            if initial_messages:
                self.storage.add_messages(thread_data["id"], initial_messages)

            return thread_data, 201

        except ThreadExistsError:
            raise ThreadConflictError("Thread already exists")

    def handle_append_messages(self, thread_id: str, request_data: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
        messages = request_data.get("messages", [])
        if not isinstance(messages, list) or not messages:
            raise InvalidRequestError("Messages array is required and cannot be empty")

        try:
            created_messages = self.storage.add_messages(thread_id, messages)
            return created_messages, 200
        except ThreadNotFoundError:
            raise

    def handle_list_messages(self, thread_id: str) -> tuple[list[dict[str, Any]], int]:
        try:
            messages = self.storage.get_messages(thread_id)
            return messages, 200
        except ThreadNotFoundError:
            raise


class ThreadError(Exception):
    pass


class ThreadNotFoundError(ThreadError):
    pass


class ThreadExistsError(ThreadError):
    pass


class ThreadConflictError(ThreadError):
    pass


class InvalidRequestError(ThreadError):
    pass


# Global instance
thread_storage = ThreadStorage()
thread_handler = ThreadHandler(thread_storage)
