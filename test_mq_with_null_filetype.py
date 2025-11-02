#!/usr/bin/env python3
"""
Test script to validate MQ message with null/missing fileType
"""

import json
from pydantic import ValidationError
from src.models import KnowledgeCreateMessage, KnowledgeMessageMetadata

def test_mq_with_null_filetype():
    """Test MQ message validation with null/missing fileType"""
    print("🔍 Testing MQ Message with Null/Missing fileType")
    print("=" * 60)
    
    # Test cases based on your original message format
    test_cases = [
        {
            "name": "Original message with fileType: null",
            "message": {
                "metadata": {
                    "knowledgeId": "01K8ZGEBY6RARKF7ZVXSDRTHQW",
                    "type": "ARTICLE",
                    "access": "TENANT",
                    "tenantId": "01K8ZEGGNQGZ8AM7XKS1DWSHEK",
                    "accessUserIds": ["01K8YYWDRGK7Y5SA6W95SVAA1J"]
                },
                "fileType": None,  # Explicitly null
                "fileUrls": [],
                "content": "Admin Fee content..."
            }
        },
        {
            "name": "Message without fileType field",
            "message": {
                "metadata": {
                    "knowledgeId": "01K8ZGEBY6RARKF7ZVXSDRTHQW",
                    "type": "ARTICLE",
                    "access": "TENANT",
                    "tenantId": "01K8ZEGGNQGZ8AM7XKS1DWSHEK",
                    "accessUserIds": ["01K8YYWDRGK7Y5SA6W95SVAA1J"]
                },
                # fileType field completely omitted
                "fileUrls": [],
                "content": "Admin Fee content..."
            }
        },
        {
            "name": "Message with empty string fileType",
            "message": {
                "metadata": {
                    "knowledgeId": "01K8ZGEBY6RARKF7ZVXSDRTHQW",
                    "type": "ARTICLE",
                    "access": "TENANT",
                    "tenantId": "01K8ZEGGNQGZ8AM7XKS1DWSHEK",
                    "accessUserIds": ["01K8YYWDRGK7Y5SA6W95SVAA1J"]
                },
                "fileType": "",  # Empty string
                "fileUrls": [],
                "content": "Admin Fee content..."
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test_case['name']}")
        print("-" * 50)
        
        try:
            # Try to validate the message
            validated_message = KnowledgeCreateMessage(**test_case["message"])
            print(f"✅ VALID")
            print(f"   fileType value: {repr(validated_message.fileType)}")
            print(f"   Message validated successfully")
            
        except ValidationError as e:
            print(f"❌ INVALID")
            print(f"   Validation Error: {e}")
            for error in e.errors():
                print(f"   Field: {error.get('loc', 'unknown')}")
                print(f"   Message: {error.get('msg', 'unknown')}")
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Test Results Summary:")
    print("- null fileType should be accepted")
    print("- Missing fileType field should be accepted")
    print("- Empty string fileType should be handled appropriately")

if __name__ == "__main__":
    test_mq_with_null_filetype()