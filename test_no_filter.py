#!/usr/bin/env python3
"""
Test script to demonstrate NO_FILTER functionality
"""

import requests
import json
import time

def test_chat_with_user_attributes(user_attributes, description):
    """Test chat with specific user attributes"""
    print(f"\n🔍 Testing: {description}")
    print(f"   User attributes: {user_attributes}")
    
    url = "http://localhost:8000/chat/stream-sse"
    
    payload = {
        "chatHistory": [],  # Empty chat history for this test
        "message": "What is Python?",
        "userAttributes": user_attributes
    }
    
    try:
        response = requests.post(url, json=payload, stream=True, timeout=30)
        response.raise_for_status()
        
        # Count response chunks
        chunk_count = 0
        for line in response.iter_lines():
            if line:
                chunk_count += 1
        
        print(f"   ✅ Response received: {chunk_count} chunks")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("🧪 NO_FILTER Functionality Test")
    print("=" * 60)
    
    # Test with valid tenant
    valid_user = {
        "userId": "user-123",
        "operationIds": ["CHAT_READ"],
        "userTenants": [
            {
                "tenantId": "test_tenant_123",
                "tenantRole": "user"
            }
        ]
    }
    
    # Test with invalid tenant (should fail without NO_FILTER, succeed with NO_FILTER)
    invalid_user = {
        "userId": "user-456",
        "operationIds": ["CHAT_READ"],
        "userTenants": [
            {
                "tenantId": "invalid_tenant_999",
                "tenantRole": "user"
            }
        ]
    }
    
    # Test with no tenants (should fail without NO_FILTER, succeed with NO_FILTER)
    no_tenant_user = {
        "userId": "user-789",
        "operationIds": ["CHAT_READ"],
        "userTenants": []
    }
    
    # Run tests
    test_chat_with_user_attributes(valid_user, "Valid tenant user")
    test_chat_with_user_attributes(invalid_user, "Invalid tenant user")
    test_chat_with_user_attributes(no_tenant_user, "No tenant user")
    
    print(f"\n🎉 Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()