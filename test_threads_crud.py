#!/usr/bin/env python3
"""Test script for threads CRUD operations."""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_threads_crud():
    """Test the complete CRUD operations for threads."""
    try:
        from threads import thread_handler

        print("Testing Threads CRUD Operations")
        print("=" * 40)

        # Test 1: Create a thread
        print("\n1. Testing CREATE thread...")
        create_data = {
            "metadata": {"userId": "test123", "topic": "testing"},
            "messages": [{"role": "user", "content": "Hello!"}]
        }

        thread_result, status = thread_handler.handle_create_thread(create_data)
        thread_id = thread_result["id"]

        print(f"✅ Created thread: {thread_id}")
        print(f"   Status: {status}")
        print(f"   Metadata: {thread_result['metadata']}")

        # Test 2: Get the thread
        print("\n2. Testing GET thread...")
        get_result, status = thread_handler.handle_get_thread(thread_id)

        print(f"✅ Retrieved thread: {get_result['id']}")
        print(f"   Status: {status}")
        print(f"   Created at: {get_result['created_at']}")
        print(f"   Metadata: {get_result['metadata']}")

        # Test 3: Update the thread
        print("\n3. Testing UPDATE thread...")
        update_data = {
            "metadata": {"status": "active", "priority": "high"}
        }

        update_result, status = thread_handler.handle_update_thread(thread_id, update_data)

        print(f"✅ Updated thread: {update_result['id']}")
        print(f"   Status: {status}")
        print(f"   Updated metadata: {update_result['metadata']}")

        # Verify the update
        get_result2, _ = thread_handler.handle_get_thread(thread_id)
        expected_metadata = {"userId": "test123", "topic": "testing", "status": "active", "priority": "high"}

        if get_result2["metadata"] == expected_metadata:
            print("✅ Metadata update verified")
        else:
            print("❌ Metadata update failed")
            print(f"   Expected: {expected_metadata}")
            print(f"   Got: {get_result2['metadata']}")
            return False

        # Test 4: List messages (should have the initial message)
        print("\n4. Testing LIST messages...")
        messages_result, status = thread_handler.handle_list_messages(thread_id)

        print(f"✅ Listed messages: {len(messages_result)} message(s)")
        print(f"   Status: {status}")
        if messages_result:
            print(f"   First message: {messages_result[0]['content']}")

        # Test 5: Add more messages
        print("\n5. Testing APPEND messages...")
        append_data = {
            "messages": [
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "How are you?"}
            ]
        }

        append_result, status = thread_handler.handle_append_messages(thread_id, append_data)

        print(f"✅ Appended {len(append_result)} messages")
        print(f"   Status: {status}")

        # Verify total messages
        messages_result2, _ = thread_handler.handle_list_messages(thread_id)
        print(f"   Total messages now: {len(messages_result2)}")

        # Test 6: Delete the thread
        print("\n6. Testing DELETE thread...")
        delete_result, status = thread_handler.handle_delete_thread(thread_id)

        print("✅ Deleted thread")
        print(f"   Status: {status}")
        print(f"   Result: {delete_result}")

        # Test 7: Verify deletion (should fail)
        print("\n7. Testing GET deleted thread (should fail)...")
        try:
            thread_handler.handle_get_thread(thread_id)
            print("❌ Thread still exists after deletion")
            return False
        except Exception as e:
            print(f"✅ Thread properly deleted: {type(e).__name__}")

        print("\n🎉 All CRUD tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_threads_crud()
    sys.exit(0 if success else 1)
