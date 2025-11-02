#!/usr/bin/env python3
"""
Test script to validate optional fileType functionality
"""

import json
from pydantic import ValidationError
from src.models import KnowledgeCreateMessage, KnowledgeMessageMetadata

def test_optional_filetype():
    """Test that fileType is now optional and handles various scenarios"""
    print("🔍 Testing Optional fileType Validation")
    print("=" * 60)
    
    base_metadata = {
        "knowledgeId": "01K8ZGEBY6RARKF7ZVXSDRTHQW",
        "type": "ARTICLE",
        "access": "TENANT",
        "tenantId": "01K8ZEGGNQGZ8AM7XKS1DWSHEK",
        "accessUserIds": ["01K8YYWDRGK7Y5SA6W95SVAA1J"]
    }
    
    # Test cases for optional fileType
    test_cases = [
        {
            "name": "fileType with valid 'image'",
            "message": {
                "metadata": base_metadata,
                "content": "Test content",
                "fileType": "image",
                "fileUrls": []
            }
        },
        {
            "name": "fileType with valid 'IMAGE' (uppercase)",
            "message": {
                "metadata": base_metadata,
                "content": "Test content", 
                "fileType": "IMAGE",
                "fileUrls": []
            }
        },
        {
            "name": "fileType with valid 'pdf'",
            "message": {
                "metadata": base_metadata,
                "content": "Test content",
                "fileType": "pdf",
                "fileUrls": []
            }
        },
        {
            "name": "fileType with None value",
            "message": {
                "metadata": base_metadata,
                "content": "Test content",
                "fileType": None,
                "fileUrls": []
            }
        },
        {
            "name": "fileType omitted completely",
            "message": {
                "metadata": base_metadata,
                "content": "Test content",
                "fileUrls": []
                # fileType is completely omitted
            }
        },
        {
            "name": "fileType with invalid value",
            "message": {
                "metadata": base_metadata,
                "content": "Test content",
                "fileType": "invalid",
                "fileUrls": []
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
            print(f"   Full message: {validated_message.model_dump()}")
            
        except ValidationError as e:
            print(f"❌ INVALID")
            print(f"   Error: {e}")
            for error in e.errors():
                print(f"   Field: {error.get('loc', 'unknown')}")
                print(f"   Message: {error.get('msg', 'unknown')}")
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Summary:")
    print("- fileType should be optional (can be None or omitted)")
    print("- When provided, it should accept 'pdf' or 'image' (case-insensitive)")
    print("- Invalid values should still be rejected")

if __name__ == "__main__":
    test_optional_filetype()