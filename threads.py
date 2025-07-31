import time
import uuid
from typing import Any


class ThreadStorage:
    def __init__(self):
        self._threads = {}
        self._messages = {}

    def create_thread(self, thread_id: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if thread_id is None:
            thread_id = f"thread_{uuid.uuid4()}"

        if thread_id in self._threads:
            msg = f"Thread {thread_id} already exists"
            raise ThreadExistsError(msg)

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
            msg = f"Thread {thread_id} not found"
            raise ThreadNotFoundError(msg)
        return self._threads[thread_id]

    def add_messages(self, thread_id: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if thread_id not in self._threads:
            msg = f"Thread {thread_id} not found"
            raise ThreadNotFoundError(msg)

        created_messages = []
        for msg in messages:
            message_id = f"msg_{uuid.uuid4()}"
            message_data = self._create_message_data(message_id, thread_id, msg)
            self._messages[thread_id].append(message_data)
            created_messages.append(message_data)

        return created_messages

    def get_messages(self, thread_id: str) -> list[dict[str, Any]]:
        if thread_id not in self._threads:
            msg = f"Thread {thread_id} not found"
            raise ThreadNotFoundError(msg)
        return self._messages.get(thread_id, [])

    def update_thread(self, thread_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
        if thread_id not in self._threads:
            msg = f"Thread {thread_id} not found"
            raise ThreadNotFoundError(msg)

        # Update the metadata
        self._threads[thread_id]["metadata"].update(metadata)

        return self._threads[thread_id]

    def delete_thread(self, thread_id: str) -> bool:
        if thread_id not in self._threads:
            msg = f"Thread {thread_id} not found"
            raise ThreadNotFoundError(msg)

        # Remove thread and its messages
        del self._threads[thread_id]
        if thread_id in self._messages:
            del self._messages[thread_id]

        return True

    def update_thread(self, thread_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
        if thread_id not in self._threads:
            msg = f"Thread {thread_id} not found"
            raise ThreadNotFoundError(msg)

        # Update the metadata
        self._threads[thread_id]["metadata"].update(metadata)

        return self._threads[thread_id]

    def delete_thread(self, thread_id: str) -> bool:
        if thread_id not in self._threads:
            msg = f"Thread {thread_id} not found"
            raise ThreadNotFoundError(msg)

        # Remove thread and its messages
        del self._threads[thread_id]
        if thread_id in self._messages:
            del self._messages[thread_id]

        return True

    def _create_message_data(self, message_id: str, thread_id: str, message_dict: dict[str, Any]) -> dict[str, Any]:
        # Validate required fields
        if "role" not in message_dict:
            msg = "Message must have a 'role' field"
            raise ValueError(msg)

        # Build message with proper null handling for Langbase compatibility
        return {
            "id": message_id,
            "thread_id": thread_id,
            "created_at": int(time.time()),
            "role": message_dict["role"],
            "content": message_dict.get("content"),  # Can be null for tool calls
            "tool_call_id": message_dict.get("tool_call_id"),  # null if not a tool response
            "tool_calls": message_dict.get("tool_calls") or [],  # Empty array if no tool calls
            "name": message_dict.get("name"),  # null if no name specified
            "attachments": message_dict.get("attachments") or [],  # Empty array if no attachments
            "metadata": message_dict.get("metadata") or {},  # Empty object if no metadata
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
            msg = "Thread already exists"
            raise ThreadConflictError(msg)

    def handle_append_messages(self, thread_id: str, request_data: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
        messages = request_data.get("messages", [])
        if not isinstance(messages, list) or not messages:
            msg = "Messages array is required and cannot be empty"
            raise InvalidRequestError(msg)

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

    def handle_get_thread(self, thread_id: str) -> tuple[dict[str, Any], int]:
        try:
            thread_data = self.storage.get_thread(thread_id)
            return thread_data, 200
        except ThreadNotFoundError:
            raise

    def handle_update_thread(self, thread_id: str, request_data: dict[str, Any]) -> tuple[dict[str, Any], int]:
        metadata = request_data.get("metadata", {})
        if not isinstance(metadata, dict):
            msg = "Metadata must be a dictionary"
            raise InvalidRequestError(msg)

        try:
            updated_thread = self.storage.update_thread(thread_id, metadata)
            return updated_thread, 200
        except ThreadNotFoundError:
            raise

    def handle_delete_thread(self, thread_id: str) -> tuple[dict[str, Any], int]:
        try:
            self.storage.delete_thread(thread_id)
            return {"success": True}, 200
        except ThreadNotFoundError:
            raise

    def handle_get_thread(self, thread_id: str) -> tuple[dict[str, Any], int]:
        try:
            thread_data = self.storage.get_thread(thread_id)
            return thread_data, 200
        except ThreadNotFoundError:
            raise

    def handle_update_thread(self, thread_id: str, request_data: dict[str, Any]) -> tuple[dict[str, Any], int]:
        metadata = request_data.get("metadata", {})
        if not isinstance(metadata, dict):
            msg = "Metadata must be a dictionary"
            raise InvalidRequestError(msg)

        try:
            updated_thread = self.storage.update_thread(thread_id, metadata)
            return updated_thread, 200
        except ThreadNotFoundError:
            raise

    def handle_delete_thread(self, thread_id: str) -> tuple[dict[str, Any], int]:
        try:
            self.storage.delete_thread(thread_id)
            return {"success": True}, 200
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
