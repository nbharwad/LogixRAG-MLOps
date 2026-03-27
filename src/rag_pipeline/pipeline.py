import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import time

from src.config import get_config
from src.ingestion.chunker import DocumentChunker, load_raw_documents
from src.embeddings.generator import EmbeddingGenerator
from src.retrieval.vector_store import VectorStore, load_chunks, load_embeddings
from src.reranker.reranker import Reranker
from src.pii.masker import PIIMasker


@dataclass
class RAGResponse:
    answer: str
    sources: List[Dict[str, Any]]
    latency_ms: float
    pii_detected: bool
    pii_count: int


class RAGPipeline:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.chunker = DocumentChunker(self.config)
        self.embedder = EmbeddingGenerator(self.config)
        self.vector_store = VectorStore(self.config)
        self.reranker = Reranker(self.config)
        self.pii_masker = PIIMasker(self.config)
        self._initialized = False
    
    def initialize(self, rebuild_index: bool = False):
        if self._initialized and not rebuild_index:
            return
        
        chunks = load_chunks()
        embeddings = load_embeddings()
        
        if rebuild_index:
            self.vector_store.delete_collection()
        
        self.vector_store.insert_chunks(chunks, embeddings)
        self._initialized = True
        print("RAG pipeline initialized")
    
    def retrieve(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        if not self._initialized:
            self.initialize()
        
        k = top_k or self.config.rag.top_k
        
        retrieved_chunks = self.vector_store.search(query, top_k=k * 2)
        
        documents = [chunk.text for chunk in retrieved_chunks]
        
        if self.reranker and documents:
            reranked = self.reranker.rerank(query, documents, top_k=k)
            reranked_ids = [i for i, d in enumerate(documents[:len(reranked)])]
            
            sources = []
            for i, r in enumerate(reranked):
                if i < len(retrieved_chunks):
                    sources.append({
                        "chunk_id": retrieved_chunks[i].chunk_id,
                        "text": r["text"],
                        "score": r["score"],
                        "policy_id": retrieved_chunks[i].policy_id,
                        "policy_type": retrieved_chunks[i].policy_type
                    })
        else:
            sources = [
                {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "score": chunk.score,
                    "policy_id": chunk.policy_id,
                    "policy_type": chunk.policy_type
                }
                for chunk in retrieved_chunks[:k]
            ]
        
        return sources[:k]
    
    def generate_answer(self, query: str, context: List[Dict[str, Any]]) -> str:
        context_text = "\n\n".join([
            f"Source {i+1}: {s['text']}" 
            for i, s in enumerate(context)
        ])
        
        prompt = f"""You are a helpful insurance policy assistant. Answer the user's question based only on the provided sources.

Sources:
{context_text}

Question: {query}

Answer:"""
        
        try:
            import httpx
            response = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.config.llm.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.config.llm.temperature,
                        "num_predict": self.config.llm.max_tokens
                    }
                },
                timeout=60.0
            )
            if response.status_code == 200:
                return response.json().get("response", "No response generated")
        except Exception as e:
            pass
        
        return f"Based on the retrieved sources: {context[0]['text'][:200]}..." if context else "No context available"
    
    def query(self, query: str, mask_pii: bool = True) -> RAGResponse:
        start_time = time.time()
        
        if mask_pii:
            pii_result = self.pii_masker.mask(query)
            query_to_use = pii_result.text
            pii_detected = pii_result.pii_count > 0
            pii_count = pii_result.pii_count
        else:
            query_to_use = query
            pii_detected = False
            pii_count = 0
        
        sources = self.retrieve(query_to_use)
        
        answer = self.generate_answer(query_to_use, sources)
        
        latency_ms = (time.time() - start_time) * 1000
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            latency_ms=latency_ms,
            pii_detected=pii_detected,
            pii_count=pii_count
        )
    
    def get_stats(self) -> Dict[str, Any]:
        if not self._initialized:
            return {"initialized": False}
        
        info = self.vector_store.get_collection_info()
        return {
            "initialized": self._initialized,
            "collection": info,
            "chunk_size": self.config.rag.chunk_size,
            "top_k": self.config.rag.top_k,
            "embedding_model": self.config.rag.embedding_model
        }


def build_index(config_path: str = None):
    import yaml
    
    if config_path:
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        config = get_config()
    else:
        config = get_config()
    
    print("Building RAG index...")
    print("=" * 50)
    
    print("\n1. Loading documents...")
    documents = load_raw_documents()
    print(f"   Loaded {len(documents)} documents")
    
    print("\n2. Chunking documents...")
    chunker = DocumentChunker(config)
    chunks = chunker.process_documents(documents)
    print(f"   Created {len(chunks)} chunks")
    
    output_path = Path(str(config.data.processed_path)) / "chunks.jsonl"
    chunker.save_chunks(chunks, str(output_path))
    print(f"   Saved chunks to {output_path}")
    
    print("\n3. Generating embeddings...")
    embedder = EmbeddingGenerator(config)
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedder.encode_documents(texts)
    print(f"   Generated {embeddings.shape[0]} embeddings, dimension: {embeddings.shape[1]}")
    
    emb_path = Path(str(config.data.processed_path)) / "embeddings.npy"
    with open(emb_path, 'wb') as f:
        np.save(f, embeddings)
    print(f"   Saved embeddings to {emb_path}")
    
    print("\n4. Building vector store...")
    from src.retrieval.vector_store import VectorStore
    import numpy as np
    store = VectorStore(config)
    store.insert_chunks(chunks, embeddings)
    print(f"   Vector store built successfully")
    
    print("\n" + "=" * 50)
    print("RAG index build complete!")
    
    return {
        "documents": len(documents),
        "chunks": len(chunks),
        "embeddings": embeddings.shape[0],
        "dimension": embeddings.shape[1]
    }


if __name__ == "__main__":
    import numpy as np
    
    pipeline = RAGPipeline()
    pipeline.initialize()
    
    query = "What is the pre-existing conditions waiting period?"
    result = pipeline.query(query)
    
    print(f"\nQuery: {query}")
    print(f"Answer: {result.answer}")
    print(f"Latency: {result.latency_ms:.2f}ms")
    print(f"Sources: {len(result.sources)}")
