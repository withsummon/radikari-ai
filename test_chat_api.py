#!/usr/bin/env python3
"""
Test Chat API - Tests HTTP endpoints for chat functionality
"""
import asyncio
import aiohttp
import json
from datetime import datetime

class TestChatAPI:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = None

    async def create_session(self):
        """Create HTTP session"""
        self.session = aiohttp.ClientSession()

    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()

    async def test_health_check(self):
        """Test health check endpoint"""
        print("🏥 Testing health check...")
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check passed: {data}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

    async def test_stats_endpoint(self):
        """Test statistics endpoint"""
        print("📊 Testing stats endpoint...")
        try:
            async with self.session.get(f"{self.base_url}/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Stats retrieved: {data}")
                    return data
                else:
                    print(f"❌ Stats failed: {response.status}")
                    return None
        except Exception as e:
            print(f"❌ Stats error: {e}")
            return None

    async def test_chat_send(self, message, tenant_id="company_a"):
        """Test /chat/send endpoint"""
        print(f"💬 Testing chat send: '{message}'")
        
        payload = {
            "message": message,
            "chathistory": {
                "messages": []
            },
            "user_attributes": {
                "userId": "user123",
                "operationIds": ["read", "write"],
                "userTenants": [
                    {
                        "tenantId": tenant_id,
                        "tenantRole": "admin"
                    }
                ]
            }
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/chat/send",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Chat response received:")
                    print(f"   Response: {data.get('response', 'No response')}")
                    print(f"   Sources: {len(data.get('sources', []))} documents")
                    if data.get('sources'):
                        for i, source in enumerate(data['sources'][:2]):  # Show first 2 sources
                            print(f"   Source {i+1}: {source.get('metadata', {}).get('title', 'Unknown')}")
                    return data
                else:
                    error_text = await response.text()
                    print(f"❌ Chat send failed: {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"❌ Chat send error: {e}")
            return None

    async def test_chat_stream(self, message, tenant_id="company_a"):
        """Test /chat/stream endpoint"""
        print(f"🌊 Testing chat stream: '{message}'")
        
        payload = {
            "message": message,
            "chathistory": {
                "messages": []
            },
            "user_attributes": {
                "userId": "user123",
                "operationIds": ["read", "write"],
                "userTenants": [
                    {
                        "tenantId": tenant_id,
                        "tenantRole": "admin"
                    }
                ]
            }
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/chat/stream",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    print("✅ Stream started, receiving chunks:")
                    full_response = ""
                    chunk_count = 0
                    
                    async for line in response.content:
                        if line:
                            line_str = line.decode('utf-8').strip()
                            if line_str.startswith('data: '):
                                chunk_data = line_str[6:]  # Remove 'data: ' prefix
                                if chunk_data != '[DONE]':
                                    try:
                                        chunk_json = json.loads(chunk_data)
                                        if chunk_json.get('type') == 'content':
                                            content = chunk_json.get('content', '')
                                            full_response += content
                                            chunk_count += 1
                                            if chunk_count <= 3:  # Show first few chunks
                                                print(f"   Chunk {chunk_count}: '{content}'")
                                    except json.JSONDecodeError:
                                        pass
                    
                    print(f"✅ Stream completed: {chunk_count} chunks, {len(full_response)} characters")
                    return {"response": full_response, "chunks": chunk_count}
                else:
                    error_text = await response.text()
                    print(f"❌ Chat stream failed: {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"❌ Chat stream error: {e}")
            return None

    async def run_test_suite(self):
        """Run complete chat API test suite"""
        print("🚀 Starting Chat API Test Suite...")
        
        # Test 1: Health check
        print("\n" + "="*50)
        health_ok = await self.test_health_check()
        if not health_ok:
            print("❌ Health check failed, stopping tests")
            return
        
        # Test 2: Stats
        print("\n" + "="*50)
        await self.test_stats_endpoint()
        
        # Test 3: Chat send - general question
        print("\n" + "="*50)
        await self.test_chat_send("What is machine learning?")
        
        # Wait a bit between tests
        await asyncio.sleep(2)
        
        # Test 4: Chat send - specific question
        print("\n" + "="*50)
        await self.test_chat_send("Tell me about deep learning and neural networks")
        
        await asyncio.sleep(2)
        
        # Test 5: Chat stream
        print("\n" + "="*50)
        await self.test_chat_stream("Explain the difference between machine learning and deep learning")
        
        await asyncio.sleep(2)
        
        # Test 6: Test with different tenant
        print("\n" + "="*50)
        print("🏢 Testing with different tenant (should have no knowledge)...")
        await self.test_chat_send("What is machine learning?", tenant_id="company_b")
        
        print("\n✅ Chat API test suite completed!")

async def main():
    tester = TestChatAPI()
    
    try:
        await tester.create_session()
        await tester.run_test_suite()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await tester.close_session()

if __name__ == "__main__":
    asyncio.run(main())