#!/usr/bin/env python3
"""
Test script to verify HTTP connection behavior after SSE streaming completes.
"""

import socket
import time
import json


def test_connection_closure():
    """Test if HTTP connection closes properly after streaming completes."""
    print("Testing HTTP connection closure behavior...")
    
    # Create a raw socket connection
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(15)  # 15 second timeout
    
    try:
        # Connect to server
        sock.connect(('localhost', 8000))
        print("✓ Connected to server")
        
        # Send HTTP request
        request = (
            "POST /v1/pipes/run HTTP/1.1\r\n"
            "Host: localhost:8000\r\n"
            "Content-Type: application/json\r\n"
            "Content-Length: 68\r\n"
            "Connection: close\r\n"  # Explicitly request connection close
            "\r\n"
            '{"messages": [{"role": "user", "content": "Hello"}], "stream": true}'
        )
        
        sock.send(request.encode())
        print("✓ Sent request")
        
        # Read response
        response_data = b""
        chunks_received = 0
        done_received = False
        
        start_time = time.time()
        
        while True:
            try:
                data = sock.recv(1024)
                if not data:
                    print("✓ Connection closed by server (recv returned empty)")
                    break
                
                response_data += data
                response_str = data.decode('utf-8', errors='ignore')
                
                # Count chunks and look for [DONE]
                if 'data: [DONE]' in response_str:
                    done_received = True
                    print("✓ Received [DONE] marker")
                
                # Count data chunks (excluding [DONE])
                lines = response_str.split('\n')
                for line in lines:
                    if line.startswith('data: ') and not line.endswith('[DONE]'):
                        try:
                            json_data = line[6:].strip()
                            if json_data and json_data != '[DONE]':
                                json.loads(json_data)  # Validate JSON
                                chunks_received += 1
                        except json.JSONDecodeError:
                            pass
                
                # If we received [DONE], wait a bit more to see if connection closes
                if done_received:
                    print(f"✓ Received {chunks_received} data chunks")
                    print("⏳ Waiting to see if connection closes...")
                    time.sleep(2)  # Wait 2 seconds after [DONE]
                    
            except socket.timeout:
                elapsed = time.time() - start_time
                if done_received:
                    print(f"❌ Connection still open {elapsed:.1f}s after [DONE] - TIMEOUT")
                    return False
                else:
                    print(f"❌ Timeout waiting for response after {elapsed:.1f}s")
                    return False
            except ConnectionResetError:
                print("✓ Connection reset by server")
                break
            except Exception as e:
                print(f"❌ Error reading response: {e}")
                return False
        
        elapsed = time.time() - start_time
        print(f"✓ Total duration: {elapsed:.1f}s")
        
        if done_received:
            print("✅ Connection closed properly after streaming completed")
            return True
        else:
            print("❌ Did not receive [DONE] marker")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False
    finally:
        sock.close()


def test_with_curl_verbose():
    """Test connection behavior using curl with verbose output."""
    print("\nTesting with curl verbose output...")
    import subprocess
    
    try:
        # Run curl with verbose output and timeout
        result = subprocess.run([
            'curl', '-v', '--max-time', '10',
            '-X', 'POST', 'http://localhost:8000/v1/pipes/run',
            '-H', 'Content-Type: application/json',
            '-H', 'Connection: close',
            '-d', '{"messages": [{"role": "user", "content": "Test"}], "stream": true}'
        ], capture_output=True, text=True, timeout=15)
        
        print("STDOUT:")
        print(result.stdout[-500:])  # Last 500 chars
        print("\nSTDERR:")
        print(result.stderr[-500:])  # Last 500 chars
        
        # Check if curl completed successfully
        if result.returncode == 0:
            print("✅ Curl completed successfully")
            return True
        else:
            print(f"❌ Curl failed with return code: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Curl timed out - connection likely not closed properly")
        return False
    except Exception as e:
        print(f"❌ Curl test failed: {e}")
        return False


def main():
    """Run connection behavior tests."""
    print("HTTP Connection Behavior Test")
    print("=" * 50)
    
    # Wait for server to be ready
    time.sleep(1)
    
    tests = [
        test_connection_closure,
        test_with_curl_verbose
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if passed < len(tests):
        print("⚠️  Connection may not be closing properly after streaming!")
    else:
        print("✅ Connection behavior appears correct")


if __name__ == "__main__":
    main()
