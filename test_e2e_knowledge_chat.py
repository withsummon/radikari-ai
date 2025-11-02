#!/usr/bin/env python3
"""
End-to-End Test: Add Knowledge (Text Only) and Chat
Tests the complete flow of adding knowledge without files and then querying the AI.
"""

import json
import uuid
from datetime import datetime
from src.knowledge_service import KnowledgeService
from src.vector_store import ChromaVectorStore
from src.models import KnowledgeCreateMessage

def test_e2e_knowledge_and_chat():
    """Test adding text knowledge and then chatting about it"""
    
    print("🚀 Starting End-to-End Knowledge + Chat Test")
    print("=" * 50)
    
    # Initialize services
    print("📦 Initializing services...")
    vector_store = ChromaVectorStore()
    knowledge_service = KnowledgeService(vector_store)
    
    # Test data
    tenant_id = "test_tenant_123"
    knowledge_id = str(uuid.uuid4())
    
    # Step 1: Add knowledge without file
    print("\n📚 Step 1: Adding text-based knowledge...")
    knowledge_data = {
        "metadata": {
            "knowledgeId": knowledge_id,
            "type": "ARTICLE",
            "access": "TENANT",
            "tenantId": tenant_id
        },
        "content": """
        Python is a high-level programming language known for its simplicity and readability.
        
        Key features of Python:
        - Easy to learn and use
        - Interpreted language
        - Object-oriented programming support
        - Large standard library
        - Cross-platform compatibility
        
        Python is widely used for:
        - Web development (Django, Flask)
        - Data science and machine learning
        - Automation and scripting
        - Desktop applications
        
        Basic Python syntax:
        - Variables: x = 10
        - Functions: def my_function():
        - Classes: class MyClass:
        - Loops: for item in list:
        """,
        "fileType": None,  # No file, just text content
        "fileUrls": []  # Empty list since no files
    }
    
    try:
        knowledge_message = KnowledgeCreateMessage(**knowledge_data)
        result = knowledge_service.process_knowledge_create_message(knowledge_message.dict())
        
        if result.get("status") == "success":
            print(f"✅ Knowledge added successfully!")
            print(f"   - Knowledge ID: {knowledge_id}")
            print(f"   - Chunks created: {len(result.get('chunk_ids', []))}")
        else:
            print(f"❌ Failed to add knowledge: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error adding knowledge: {e}")
        return False
    
    # Step 2: Wait a moment for indexing
    print("\n⏳ Waiting for knowledge indexing...")
    import time
    time.sleep(2)
    
    # Step 3: Test chat queries about the knowledge
    print("\n💬 Step 2: Testing chat queries...")
    
    test_queries = [
        "What is Python?",
        "What are the key features of Python?",
        "What is Python used for?",
        "How do you define a function in Python?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Query {i}: {query}")
        
        try:
            chat_request = {
                "chatHistory": [],
                "message": query,
                "userAttributes": {
                    "userId": "test-user-123",
                    "operationIds": ["CHAT_READ"],
                    "userTenants": [
                        {
                            "tenantId": tenant_id,
                            "tenantRole": "user"
                        }
                    ]
                }
            }
            
            # Test via API endpoint (streaming)
            import requests
            response = requests.post(
                "http://localhost:8000/chat/stream-sse",
                json=chat_request,
                stream=True,
                headers={"Accept": "text/event-stream"}
            )
            
            if response.status_code == 200:
                response_text = ""
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data = line_str[6:]  # Remove 'data: ' prefix
                            if data.strip() and data != '[DONE]':
                                response_text += data
                
                if response_text:
                    print(f"✅ Response received ({len(response_text)} chars)")
                    print(f"   Preview: {response_text[:100]}...")
                    
                    # Check if response seems relevant to Python
                    if any(keyword in response_text.lower() for keyword in ['python', 'programming', 'language']):
                        print(f"✅ Response appears relevant to the knowledge base")
                    else:
                        print(f"⚠️  Response may not be using the knowledge base")
                else:
                    print(f"❌ No response content received")
            else:
                print(f"❌ API request failed with status {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error in chat query: {e}")
    
    # Step 4: Test search functionality
    print(f"\n🔍 Step 3: Testing direct search...")
    try:
        # Build filter for tenant access
        where_filter = {"tenantId": tenant_id}
        
        search_results = vector_store.search(
            query="Python programming features",
            n_results=3,
            where_filter=where_filter
        )
        
        print(f"✅ Search returned {len(search_results)} results")
        for i, result in enumerate(search_results, 1):
            print(f"   Result {i}: Score {result.get('score', 0):.3f}")
            print(f"   Content preview: {result.get('content', '')[:80]}...")
            
    except Exception as e:
        print(f"❌ Error in search: {e}")
    
    print(f"\n🎉 End-to-End test completed!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    test_e2e_knowledge_and_chat()