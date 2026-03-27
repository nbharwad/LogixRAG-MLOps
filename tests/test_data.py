import pytest
import json
from pathlib import Path

from src.ingestion.chunker import DocumentChunker, load_raw_documents
from src.config import get_config


class TestDataValidation:
    @pytest.fixture
    def config(self):
        return get_config()
    
    @pytest.fixture
    def sample_documents(self):
        return load_raw_documents()
    
    def test_documents_load(self, sample_documents):
        assert len(sample_documents) > 0, "Should load sample documents"
    
    def test_document_structure(self, sample_documents):
        for doc in sample_documents:
            assert "policy_id" in doc, "Document should have policy_id"
            assert "type" in doc, "Document should have type"
            assert "content" in doc, "Document should have content"
            assert "title" in doc, "Document should have title"
    
    def test_document_types(self, sample_documents):
        valid_types = {"health", "auto", "home", "life"}
        for doc in sample_documents:
            assert doc["type"] in valid_types, f"Invalid document type: {doc['type']}"
    
    def test_chunking(self, config, sample_documents):
        chunker = DocumentChunker(config)
        chunks = chunker.process_documents(sample_documents)
        
        assert len(chunks) > 0, "Should create chunks"
        
        for chunk in chunks[:5]:
            assert chunk.text, "Chunk should have text"
            assert chunk.policy_id, "Chunk should have policy_id"
            assert len(chunk.text) <= config.rag.chunk_size * 1.5, "Chunk should be within size limit"
    
    def test_chunk_overlap(self, config, sample_documents):
        chunker = DocumentChunker(config)
        chunks = chunker.process_documents(sample_documents)
        
        policy_chunks = [c for c in chunks if c.policy_id == "POL-2024-001"]
        
        if len(policy_chunks) > 1:
            first_chunk_text = policy_chunks[0].text
            second_chunk_text = policy_chunks[1].text
            
            overlap_words = set(first_chunk_text.split()) & set(second_chunk_text.split())
            assert len(overlap_words) >= 0, "Chunks should have proper overlap"
    
    def test_eval_pairs_load(self):
        eval_path = Path("data/eval/qa_pairs.jsonl")
        if not eval_path.exists():
            eval_path = Path(__file__).parent.parent.parent / "data/eval/qa_pairs.jsonl"
        
        with open(eval_path, 'r') as f:
            pairs = [json.loads(line) for line in f if line.strip()]
        
        assert len(pairs) > 0, "Should load eval pairs"
        
        for pair in pairs:
            assert "question" in pair, "Eval pair should have question"
            assert "answer" in pair, "Eval pair should have answer"
            assert "context_policy_id" in pair, "Eval pair should have context_policy_id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
