#!/usr/bin/env python3
"""Test script for variables support."""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_variable_processor():
    """Test the VariableProcessor class directly."""
    try:
        # Import the class
        from pipes import VariableProcessor
        print("✅ VariableProcessor imported successfully")

        # Test basic substitution
        content = "Hello {{name}}, you are a {{profession}}!"
        variables = {"name": "Alice", "profession": "developer"}
        result = VariableProcessor.substitute_variables(content, variables)

        expected = "Hello Alice, you are a developer!"
        print(f"Input: {content}")
        print(f"Variables: {variables}")
        print(f"Output: {result}")
        print(f"Expected: {expected}")

        if result == expected:
            print("✅ Basic substitution test passed")
        else:
            print("❌ Basic substitution test failed")
            return False

        # Test message processing
        messages = [
            {"role": "user", "content": "Hi {{name}}!"},
            {"role": "assistant", "content": "Hello! How can I help you, {{name}}?"}
        ]
        variables = {"name": "Bob"}
        processed = VariableProcessor.process_messages(messages, variables)

        expected_messages = [
            {"role": "user", "content": "Hi Bob!"},
            {"role": "assistant", "content": "Hello! How can I help you, Bob?"}
        ]

        print("\nMessage processing test:")
        print(f"Input: {messages}")
        print(f"Output: {processed}")
        print(f"Expected: {expected_messages}")

        if processed == expected_messages:
            print("✅ Message processing test passed")
        else:
            print("❌ Message processing test failed")
            return False

        # Test edge cases
        print("\nTesting edge cases...")

        # Empty variables
        result = VariableProcessor.substitute_variables("Hello {{name}}", {})
        if result == "Hello {{name}}":
            print("✅ Empty variables test passed")
        else:
            print("❌ Empty variables test failed")
            return False

        # Missing variable
        result = VariableProcessor.substitute_variables("Hello {{name}} and {{missing}}", {"name": "Alice"})
        if result == "Hello Alice and {{missing}}":
            print("✅ Missing variable test passed")
        else:
            print("❌ Missing variable test failed")
            return False

        # None value
        result = VariableProcessor.substitute_variables("Hello {{name}}", {"name": None})
        if result == "Hello ":
            print("✅ None value test passed")
        else:
            print("❌ None value test failed")
            return False

        print("\n🎉 All tests passed!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_variable_processor()
    sys.exit(0 if success else 1)
