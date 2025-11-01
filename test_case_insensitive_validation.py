#!/usr/bin/env python3
"""
Test script to verify case-insensitive fileType validation
"""

import json
from pydantic import ValidationError
from src.models import KnowledgeCreateMessage, KnowledgeMessageMetadata

def test_case_insensitive_validation():
    """Test that fileType validation is now case-insensitive"""
    print("🔍 Testing Case-Insensitive fileType Validation")
    print("=" * 60)
    
    # Test cases with different case variations
    test_cases = [
        {"fileType": "image", "description": "lowercase 'image'"},
        {"fileType": "IMAGE", "description": "uppercase 'IMAGE'"},
        {"fileType": "Image", "description": "mixed case 'Image'"},
        {"fileType": "pdf", "description": "lowercase 'pdf'"},
        {"fileType": "PDF", "description": "uppercase 'PDF'"},
        {"fileType": "Pdf", "description": "mixed case 'Pdf'"},
        {"fileType": "INVALID", "description": "invalid type 'INVALID'"},
    ]
    
    base_message = {
        "metadata": {
            "knowledgeId": "01K8ZGEBY6RARKF7ZVXSDRTHQW",
            "type": "ARTICLE",
            "access": "TENANT",
            "tenantId": "01K8ZEGGNQGZ8AM7XKS1DWSHEK",
            "accessUserIds": ["01K8YYWDRGK7Y5SA6W95SVAA1J"]
        },
        "fileUrls": [],
        "content": "Test content"
    }
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing {test_case['description']}")
        print("-" * 40)
        
        # Create test message with the specific fileType
        test_message = {**base_message, "fileType": test_case["fileType"]}
        
        try:
            # Try to validate the message
            validated_message = KnowledgeCreateMessage(**test_message)
            print(f"✅ VALID: fileType '{test_case['fileType']}' -> '{validated_message.fileType}'")
            
        except ValidationError as e:
            print(f"❌ INVALID: fileType '{test_case['fileType']}'")
            print(f"   Error: {e.errors()[0]['msg']}")
    
    print("\n" + "=" * 60)
    print("🎯 Summary:")
    print("- Valid fileTypes (case-insensitive): 'pdf', 'image'")
    print("- All case variations of 'pdf' and 'image' should be accepted")
    print("- Invalid types should still be rejected")

if __name__ == "__main__":
    test_case_insensitive_validation()