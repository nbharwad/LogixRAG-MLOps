import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.rag_pipeline.pipeline import RAGPipeline, RAGResponse
from src.retrieval.vector_store import VectorStore, load_chunks
from src.config import get_config


class TestRAGBehavior:
    @pytest.fixture
    def config(self):
        return get_config()
    
    @pytest.fixture
    def pipeline(self, config):
        return RAGPipeline(config)
    
    def test_pipeline_initializes(self, pipeline):
        assert pipeline is not None
        assert pipeline.config is not None
    
    def test_vector_store_search(self):
        store = VectorStore()
        
        chunks = [
            {
                "chunk_id": "test_1",
                "text": "Health insurance covers hospitalization",
                "policy_id": "POL-001",
                "policy_type": "health"
            },
            {
                "chunk_id": "test_2", 
                "text": "Auto insurance covers vehicle damage",
                "policy_id": "POL-002",
                "policy_type": "auto"
            }
        ]
        
        import numpy as np
        embeddings = np.array([[0.1] * 384, [0.2] * 384])
        
        store.insert_chunks(chunks, embeddings)
        
        results = store.search("health insurance")
        
        assert len(results) > 0
    
    def test_pipeline_query_structure(self):
        mock_response = RAGResponse(
            answer="Test answer",
            sources=[{"text": "source"}],
            latency_ms=100.0,
            pii_detected=False,
            pii_count=0
        )
        
        assert mock_response.answer == "Test answer"
        assert mock_response.latency_ms == 100.0
        assert mock_response.pii_detected is False
    
    def test_pii_masking_in_pipeline(self):
        pipeline = RAGPipeline()
        
        query_with_pii = "My SSN is 123-45-6789, what is coverage?"
        pii_result = pipeline.pii_masker.mask(query_with_pii)
        
        assert pii_result.pii_count > 0
        assert "[REDACTED]" in pii_result.text
    
    def test_retrieval_returns_sources(self):
        chunks = load_chunks()
        
        if chunks:
            assert len(chunks) > 0
            assert "text" in chunks[0]
            assert "policy_id" in chunks[0]
    
    def test_config_loaded(self, config):
        assert config.rag.chunk_size == 512
        assert config.rag.chunk_overlap == 50
        assert config.rag.top_k == 5
        assert config.validation.faithfulness_threshold == 0.85
        assert config.validation.pii_leak_tolerance == 0
    
    def test_validation_thresholds(self, config):
        assert config.validation.p99_sla_ms == 3000
        assert config.validation.p95_sla_ms == 2500
        assert config.validation.precision_threshold == 0.88
        assert config.validation.recall_threshold == 0.85


class TestModelGates:
    @pytest.fixture
    def config(self):
        return get_config()
    
    def test_all_gates_pass(self, config):
        from validation.model_gates import RAGPromotionGate, ValidationMetrics
        from datetime import datetime
        
        gate = RAGPromotionGate(config)
        
        metrics = ValidationMetrics(
            faithfulness=0.90,
            precision=0.90,
            recall=0.88,
            latency_p50_ms=400,
            latency_p95_ms=2000,
            latency_p99_ms=2800,
            pii_leak_count=0,
            retrieval_precision=0.90,
            retrieval_recall=0.88,
            timestamp=datetime.now().isoformat()
        )
        
        result = gate.validate(metrics)
        
        assert result["passed"] is True
    
    def test_pii_gate_fails(self, config):
        from validation.model_gates import RAGPromotionGate, ValidationMetrics
        from datetime import datetime
        
        gate = RAGPromotionGate(config)
        
        metrics = ValidationMetrics(
            faithfulness=0.90,
            precision=0.90,
            recall=0.88,
            latency_p50_ms=400,
            latency_p95_ms=2000,
            latency_p99_ms=2800,
            pii_leak_count=1,
            retrieval_precision=0.90,
            retrieval_recall=0.88,
            timestamp=datetime.now().isoformat()
        )
        
        result = gate.validate(metrics)
        
        assert result["passed"] is False
        assert "pii_zero_tolerance" in result["failed_gates"]
    
    def test_latency_gate_fails(self, config):
        from validation.model_gates import RAGPromotionGate, ValidationMetrics
        from datetime import datetime
        
        gate = RAGPromotionGate(config)
        
        metrics = ValidationMetrics(
            faithfulness=0.90,
            precision=0.90,
            recall=0.88,
            latency_p50_ms=400,
            latency_p95_ms=3000,
            latency_p99_ms=4000,
            pii_leak_count=0,
            retrieval_precision=0.90,
            retrieval_recall=0.88,
            timestamp=datetime.now().isoformat()
        )
        
        result = gate.validate(metrics)
        
        assert result["passed"] is False
        assert "latency_p99" in result["failed_gates"] or "latency_p95" in result["failed_gates"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
