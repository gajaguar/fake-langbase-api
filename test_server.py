#!/usr/bin/env python3
"""
Test script for the SSE server.
"""

import json
import urllib.request
import urllib.parse
import time


def test_health_endpoint():
    """Test the health endpoint."""
    print("Testing health endpoint...")
    try:
        with urllib.request.urlopen('http://localhost:8000/health') as response:
            data = json.loads(response.read().decode())
            print(f"✓ Health check: {data}")
            return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_non_streaming():
    """Test non-streaming response."""
    print("\nTesting non-streaming response...")
    try:
        data = {
            "messages": [{"role": "user", "content": "Hello!"}],
            "stream": False
        }
        
        req = urllib.request.Request(
            'http://localhost:8000/v1/pipes/run',
            data=json.dumps(data).encode(),
            headers={'Content-Type': 'application/json'}
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
    """Test streaming response."""
    print("\nTesting streaming response...")
    try:
        data = {
            "messages": [{"role": "user", "content": "Hello!"}],
            "stream": True
        }
        
        req = urllib.request.Request(
            'http://localhost:8000/v1/pipes/run',
            data=json.dumps(data).encode(),
            headers={'Content-Type': 'application/json'}
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
                if line.startswith('data: '):
                    data_part = line[6:].strip()
                    if data_part == '[DONE]':
                        print("✓ Received [DONE] marker")
                        break
                    try:
                        chunk_data = json.loads(data_part)
                        delta_content = chunk_data['choices'][0]['delta'].get('content', '')
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


def main():
    """Run all tests."""
    print("SSE Server Test Suite")
    print("=" * 50)
    
    # Wait a moment for server to be ready
    time.sleep(1)
    
    tests = [
        test_health_endpoint,
        test_non_streaming,
        test_streaming
    ]
    
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
