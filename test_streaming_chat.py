#!/usr/bin/env python3
"""
Test script for the new streaming SSE chat endpoint with user attributes filtering.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
STREAMING_ENDPOINT = f"{BASE_URL}/chat/stream-sse"

def test_streaming_chat():
    """Test the streaming SSE chat endpoint"""
    
    # Sample test data
    test_request = {
        "chatHistory": [
            {
                "role": "user",
                "content": "Hello, I'm looking for information about our company policies.",
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "assistant", 
                "content": "Hello! I'd be happy to help you with information about company policies. What specific policy are you looking for?",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "message": "What are the vacation policies for employees?",
        "userAttributes": {
            "userId": "test-user-123",
            "operationIds": ["HR_READ", "POLICY_VIEW"],
            "userTenants": [
                {
                    "tenantId": "company-abc",
                    "tenantRole": "employee"
                }
            ]
        }
    }
    
    print("🚀 Testing Streaming SSE Chat Endpoint")
    print(f"📡 Endpoint: {STREAMING_ENDPOINT}")
    print(f"📝 Request payload:")
    print(json.dumps(test_request, indent=2))
    print("\n" + "="*50 + "\n")
    
    try:
        # Send request with streaming
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache'
        }
        
        response = requests.post(
            STREAMING_ENDPOINT,
            json=test_request,
            headers=headers,
            stream=True
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        print("\n🔄 Streaming Response:")
        print("-" * 30)
        
        if response.status_code == 200:
            # Process streaming response
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    print(f"📨 Raw line: {line}")
                    
                    # Parse SSE format
                    if line.startswith('event:'):
                        event_type = line.split(':', 1)[1].strip()
                        print(f"🎯 Event Type: {event_type}")
                    elif line.startswith('data:'):
                        data = line.split(':', 1)[1].strip()
                        try:
                            parsed_data = json.loads(data)
                            print(f"📦 Data: {json.dumps(parsed_data, indent=2)}")
                            
                            # Handle different event types
                            if parsed_data.get('type') == 'content':
                                print(f"💬 Content: {parsed_data.get('content', '')}", end='', flush=True)
                            elif parsed_data.get('type') == 'sources':
                                print(f"\n📚 Sources: {len(parsed_data.get('sources', []))} found")
                            elif parsed_data.get('type') == 'end':
                                print(f"\n✅ Stream ended")
                                break
                            elif parsed_data.get('type') == 'error':
                                print(f"\n❌ Error: {parsed_data.get('message', 'Unknown error')}")
                                break
                        except json.JSONDecodeError:
                            print(f"📄 Raw data: {data}")
                    print()
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Could not connect to the server.")
        print("💡 Make sure the RAG service is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_health_check():
    """Test if the service is running"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Service is running")
            return True
        else:
            print(f"⚠️ Service health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Service is not running")
        return False

def main():
    """Main test function"""
    print("🧪 RAG Streaming Chat Test Suite")
    print("=" * 40)
    
    # Check if service is running
    if not test_health_check():
        print("\n💡 Please start the RAG service first:")
        print("   python main.py")
        return
    
    print("\n" + "="*40)
    
    # Test streaming chat
    test_streaming_chat()
    
    print("\n" + "="*40)
    print("🏁 Test completed!")

if __name__ == "__main__":
    main()