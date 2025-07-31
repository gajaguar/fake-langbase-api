"""Variable processing functionality for Langbase API."""

import re
from typing import Any


class VariableProcessor:
    """Handles template variable substitution in messages."""

    @staticmethod
    def substitute_variables(content: str, variables: dict[str, Any]) -> str:
        """
        Substitute {{variable}} placeholders in content with values from variables dict.

        Args:
            content: String content that may contain {{variable}} placeholders
            variables: Dictionary of variable name -> value mappings

        Returns:
            String with all {{variable}} placeholders replaced with their values
        """
        if not content or not variables:
            return content

        # Pattern to match {{variable_name}} with optional whitespace
        pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"

        def replace_variable(match):
            var_name = match.group(1).strip()
            if var_name in variables:
                # Convert value to string, handling various types
                value = variables[var_name]
                if value is None:
                    return ""
                return str(value)
            # Keep the original placeholder if variable not found
            return match.group(0)

        return re.sub(pattern, replace_variable, content)

    @staticmethod
    def process_messages(messages: list[dict[str, Any]], variables: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Process a list of messages, substituting variables in content fields.

        Args:
            messages: List of message dictionaries
            variables: Dictionary of variable name -> value mappings

        Returns:
            List of messages with variable substitution applied
        """
        if not variables:
            return messages

        processed_messages = []
        for message in messages:
            # Create a copy to avoid modifying the original
            processed_message = message.copy()

            # Process content field if it exists and is a string
            if "content" in processed_message and isinstance(processed_message["content"], str):
                processed_message["content"] = VariableProcessor.substitute_variables(
                    processed_message["content"], variables
                )

            processed_messages.append(processed_message)

        return processed_messages
