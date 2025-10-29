#!/usr/bin/env python3
"""
Test script to measure streaming performance improvements
"""
import requests
import time
import json
import sys

def test_streaming_performance():
    """Test the streaming chat endpoint performance"""
    
    # Test data
    test_request = {
        "chatHistory": [
            {
                "role": "user",
                "content": "Hello, I need help with something.",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        ],
        "message": "What is artificial intelligence and how does it work?",
        "userAttributes": {
            "userId": "test-user-123",
            "operationIds": ["read", "write"],
            "userTenants": [
                {
                    "tenantId": "test-tenant",
                    "tenantRole": "user"
                }
            ]
        }
    }
    
    # Test endpoints
    endpoints = [
        ("Original (port 8001)", "http://localhost:8001/chat/stream-sse"),
        ("Optimized (port 8002)", "http://localhost:8002/chat/stream-sse")
    ]
    
    for name, url in endpoints:
        print(f"\n=== Testing {name} ===")
        
        try:
            start_time = time.time()
            first_chunk_time = None
            chunk_count = 0
            total_content = ""
            
            # Make streaming request
            response = requests.post(
                url,
                json=test_request,
                headers={"Content-Type": "application/json"},
                stream=True,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ Error: HTTP {response.status_code}")
                continue
                
            print(f"✅ Connection established")
            
            # Process streaming response
            for line in response.iter_lines(decode_unicode=True):
                if line.strip():
                    if line.startswith("data: "):
                        chunk_count += 1
                        if first_chunk_time is None:
                            first_chunk_time = time.time()
                            time_to_first_chunk = first_chunk_time - start_time
                            print(f"⚡ Time to first chunk: {time_to_first_chunk:.3f}s")
                        
                        try:
                            data = json.loads(line[6:])  # Remove "data: " prefix
                            if data.get("type") == "content":
                                content = data.get("content", "") or data.get("data", "")
                                total_content += content
                        except json.JSONDecodeError:
                            pass
                    
                    elif line.startswith("event: end"):
                        break
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print(f"📊 Performance Metrics:")
            print(f"   • Total time: {total_time:.3f}s")
            print(f"   • Chunks received: {chunk_count}")
            print(f"   • Content length: {len(total_content)} chars")
            print(f"   • Avg chunk rate: {chunk_count/total_time:.1f} chunks/sec")
            
            if total_content:
                print(f"📝 Response preview: {total_content[:100]}...")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("🚀 Streaming Performance Test")
    print("=" * 50)
    test_streaming_performance()