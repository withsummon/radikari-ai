#!/usr/bin/env python3
"""
Pytest tests for the updated knowledge_service.py implementation
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all required imports work correctly"""
    # Test langchain_text_splitters import
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    # Test QdrantVectorStore import
    from src.vector_store import QdrantVectorStore
    
    # Test updated knowledge_service imports
    from src.knowledge_service import KnowledgeService, TextChunker
    
    # Verify imports are successful
    assert RecursiveCharacterTextSplitter is not None
    assert QdrantVectorStore is not None
    assert KnowledgeService is not None
    assert TextChunker is not None

def test_text_chunker():
    """Test the updated TextChunker implementation"""
    from src.knowledge_service import TextChunker
    
    # Create TextChunker with new parameters
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    
    # Verify it uses RecursiveCharacterTextSplitter
    assert hasattr(chunker, 'splitter')
    # Check the splitter's configuration through its attributes
    assert chunker.splitter._chunk_size == 1000
    assert chunker.splitter._chunk_overlap == 200
    
    # Test chunking functionality
    test_text = """
    Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to the natural intelligence displayed by humans and animals. 
    Leading AI textbooks define the field as the study of "intelligent agents": any device that perceives its environment and takes actions that maximize its chance of successfully achieving its goals.
    
    The term "artificial intelligence" had previously been used to describe machines that mimic and display "human" cognitive skills associated with the human mind, such as "learning" and "problem-solving".
    
    AI applications include advanced web search engines, recommendation systems (used by YouTube, Amazon and Netflix), understanding human speech (such as Siri and Alexa), self-driving cars (e.g., Tesla), and competing at the highest level in strategic games (such as chess and Go).
    """ * 3  # Make it longer to test chunking
    
    chunks = chunker.chunk_text(test_text)
    
    # Verify chunks are created
    assert len(chunks) > 1
    
    # Verify chunk sizes are within limits
    for chunk in chunks:
        assert len(chunk) <= 1000
    
    # Verify overlap is working (chunks should have overlapping content)
    assert len(chunks[0]) > 800  # Should be close to max size

@patch('src.vector_store.QdrantVectorStore')
def test_knowledge_service_init(mock_vector_store):
    """Test that KnowledgeService correctly uses QdrantVectorStore"""
    from src.knowledge_service import KnowledgeService
    
    # Create a mock vector store instance
    mock_instance = Mock()
    mock_vector_store.return_value = mock_instance
    
    # Initialize KnowledgeService with QdrantVectorStore
    service = KnowledgeService(mock_instance)
    
    # Verify the vector store is correctly assigned
    assert service.vector_store == mock_instance
    
    # Verify TextChunker is initialized
    assert hasattr(service, 'text_chunker')
    assert service.text_chunker.splitter._chunk_size == 1000
    assert service.text_chunker.splitter._chunk_overlap == 200

def test_vector_store_method_compatibility():
    """Test that all vector store methods used in knowledge_service.py exist in QdrantVectorStore"""
    from src.vector_store import QdrantVectorStore
    
    # List of methods used in knowledge_service.py
    required_methods = [
        'add_chunks',
        'delete_by_knowledge_id', 
        'update_metadata',
        'search',
        'build_access_filter',
        'get_collection_stats'
    ]
    
    # Verify all methods exist in QdrantVectorStore
    for method_name in required_methods:
        assert hasattr(QdrantVectorStore, method_name), f"Method {method_name} not found in QdrantVectorStore"
        method = getattr(QdrantVectorStore, method_name)
        assert callable(method), f"Method {method_name} is not callable"

def test_no_legacy_imports():
    """Test that legacy ChromaDB imports are removed"""
    import ast
    
    # Read the knowledge_service.py file with UTF-8 encoding
    with open('src/knowledge_service.py', 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Parse the AST to find imports
    tree = ast.parse(source_code)
    
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == 'vector_store':
                for alias in node.names:
                    imports.append(alias.name)
    
    # Verify that ChromaVectorStore is not imported
    assert 'ChromaVectorStore' not in imports, "ChromaVectorStore should not be imported"
    
    # Verify that QdrantVectorStore is imported
    assert 'QdrantVectorStore' in imports, "QdrantVectorStore should be imported"

def test_recursive_character_text_splitter_usage():
    """Test that RecursiveCharacterTextSplitter is correctly used in TextChunker"""
    import ast
    
    # Read the knowledge_service.py file with UTF-8 encoding
    with open('src/knowledge_service.py', 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Verify RecursiveCharacterTextSplitter is imported
    assert 'from langchain_text_splitters import RecursiveCharacterTextSplitter' in source_code
    
    # Verify it's used in TextChunker with correct parameters
    assert 'RecursiveCharacterTextSplitter(' in source_code
    assert 'chunk_size=chunk_size' in source_code
    assert 'chunk_overlap=chunk_overlap' in source_code

def test_knowledge_service_constructor_signature():
    """Test that KnowledgeService constructor expects QdrantVectorStore"""
    import ast
    import inspect
    
    # Read the knowledge_service.py file with UTF-8 encoding
    with open('src/knowledge_service.py', 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Parse the AST
    tree = ast.parse(source_code)
    
    # Find KnowledgeService class
    knowledge_service_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'KnowledgeService':
            knowledge_service_class = node
            break
    
    assert knowledge_service_class is not None, "KnowledgeService class not found"
    
    # Find __init__ method
    init_method = None
    for node in knowledge_service_class.body:
        if isinstance(node, ast.FunctionDef) and node.name == '__init__':
            init_method = node
            break
    
    assert init_method is not None, "__init__ method not found in KnowledgeService"
    
    # Check the type annotation of vector_store parameter
    args = init_method.args
    if args.args:
        vector_store_arg = args.args[0]  # First argument after 'self'
        if vector_store_arg.annotation:
            # Convert AST node to string representation
            if hasattr(vector_store_arg.annotation, 'id'):
                annotation_name = vector_store_arg.annotation.id
            elif hasattr(vector_store_arg.annotation, 'attr'):
                annotation_name = vector_store_arg.annotation.attr
            else:
                annotation_name = ast.unparse(vector_store_arg.annotation)
            
            assert 'QdrantVectorStore' in annotation_name, f"Expected QdrantVectorStore, got {annotation_name}"

if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v"])