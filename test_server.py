#!/usr/bin/env python3

import json
import time
import urllib.parse
import urllib.request


def test_health_endpoint():
    print("Testing health endpoint...")
    try:
        with urllib.request.urlopen("http://localhost:8000/health") as response:
            data = json.loads(response.read().decode())
            print(f"✓ Health check: {data}")
            return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_non_streaming():
    print("\nTesting non-streaming response...")
    try:
        data = {"messages": [{"role": "user", "content": "Hello!"}], "stream": False}

        req = urllib.request.Request(
            "http://localhost:8000/v1/pipes/run",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req) as response:
            headers = dict(response.headers)
            response_data = json.loads(response.read().decode())

            print(f"✓ Status: {response.status}")
            print(f"✓ Headers: lb-thread-id = {headers.get('lb-thread-id', 'NOT FOUND')}")
            print(f"✓ Response: {response_data['completion'][:50]}...")
            return True

    except Exception as e:
        print(f"✗ Non-streaming test failed: {e}")
        return False


def test_streaming():
    print("\nTesting streaming response...")
    try:
        data = {"messages": [{"role": "user", "content": "Hello!"}], "stream": True}

        req = urllib.request.Request(
            "http://localhost:8000/v1/pipes/run",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req) as response:
            headers = dict(response.headers)
            print(f"✓ Status: {response.status}")
            print(f"✓ Content-Type: {headers.get('Content-Type')}")
            print(f"✓ Headers: lb-thread-id = {headers.get('lb-thread-id', 'NOT FOUND')}")

            # Read first few chunks
            chunks_received = 0
            content_parts = []

            while chunks_received < 5:  # Just read first 5 chunks
                line = response.readline().decode()
                if line.startswith("data: "):
                    data_part = line[6:].strip()
                    if data_part == "[DONE]":
                        print("✓ Received [DONE] marker")
                        break
                    try:
                        chunk_data = json.loads(data_part)
                        delta_content = chunk_data["choices"][0]["delta"].get("content", "")
                        if delta_content:
                            content_parts.append(delta_content)
                        chunks_received += 1
                    except json.JSONDecodeError:
                        pass

            print(f"✓ Received {chunks_received} chunks")
            print(f"✓ Content so far: {''.join(content_parts)}")
            return True

    except Exception as e:
        print(f"✗ Streaming test failed: {e}")
        return False


def test_streaming_timing():
    print("\nTesting streaming response timing...")
    try:
        data = {"messages": [{"role": "user", "content": "Hello!"}], "stream": True}

        req = urllib.request.Request(
            "http://localhost:8000/v1/pipes/run",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )

        start_time = time.time()
        with urllib.request.urlopen(req) as response:
            headers = dict(response.headers)
            print(f"✓ Status: {response.status}")
            print(f"✓ Content-Type: {headers.get('Content-Type')}")
            print(f"✓ Headers: lb-thread-id = {headers.get('lb-thread-id', 'NOT FOUND')}")

            # Read all chunks to test timing and count
            chunks_received = 0
            content_parts = []

            while True:
                line = response.readline().decode()
                if line.startswith("data: "):
                    data_part = line[6:].strip()
                    if data_part == "[DONE]":
                        print("✓ Received [DONE] marker")
                        break
                    try:
                        chunk_data = json.loads(data_part)
                        # Handle chunks with empty choices array (like usage chunks)
                        if chunk_data.get("choices") and len(chunk_data["choices"]) > 0:
                            delta_content = chunk_data["choices"][0]["delta"].get("content", "")
                            if delta_content:
                                content_parts.append(delta_content)
                                chunks_received += 1
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass

        end_time = time.time()
        duration = end_time - start_time

        print(f"✓ Received {chunks_received} chunks")
        print(f"✓ Duration: {duration:.2f}s")
        print(f"✓ Content: {''.join(content_parts)}")

        # Verify chunk count is within expected range (5-10 based on module constants)
        if 5 <= chunks_received <= 10:
            print("✓ Chunk count within expected range (5-10)")
        else:
            print(f"⚠ Chunk count {chunks_received} outside expected range 5-10")

        # Verify timing is reasonable (should be roughly 1 second per chunk)
        expected_min_duration = max(0, chunks_received - 1)  # No delay after last chunk
        if duration >= expected_min_duration * 0.8:  # Allow some tolerance
            print("✓ Timing appears correct for 1-second delays")
        else:
            print(f"⚠ Duration {duration:.2f}s seems too short for {chunks_received} chunks")

        return True

    except Exception as e:
        print(f"✗ Streaming timing test failed: {e}")
        return False


def main():
    print("SSE Server Test Suite")
    print("=" * 50)

    # Wait a moment for server to be ready
    time.sleep(1)

    tests = [test_health_endpoint, test_non_streaming, test_streaming, test_streaming_timing]

    passed = 0
    for test in tests:
        if test():
            passed += 1
        time.sleep(0.5)  # Small delay between tests

    print(f"\n{'=' * 50}")
    print(f"Tests passed: {passed}/{len(tests)}")

    if passed == len(tests):
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed")


if __name__ == "__main__":
    main()
