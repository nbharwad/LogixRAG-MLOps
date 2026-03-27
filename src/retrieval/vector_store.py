import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import DistanceVector, PointStruct, Filter

from src.config import get_config
from src.embeddings.generator import EmbeddingGenerator


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    policy_id: str
    policy_type: str
    score: float
    metadata: Dict[str, Any]


class VectorStore:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.collection_name = self.config.rag.collection_name
        self.top_k = self.config.rag.top_k
        self._client = None
        self._embedder = None
    
    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(location=":memory:")
        return self._client
    
    @property
    def embedder(self) -> EmbeddingGenerator:
        if self._embedder is None:
            self._embedder = EmbeddingGenerator(self.config)
        return self._embedder
    
    def create_collection(self, vector_size: int):
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "text": DistanceVector.COSINE
                }
            )
            print(f"Created collection: {self.collection_name}")
        else:
            print(f"Collection {self.collection_name} already exists")
    
    def insert_chunks(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray):
        self.create_collection(embeddings.shape[1])
        
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point = PointStruct(
                id=i,
                vector={"text": embedding.tolist()},
                payload={
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "policy_id": chunk["policy_id"],
                    "policy_type": chunk["policy_type"],
                    "source": chunk["source"],
                    "chunk_index": chunk["chunk_index"],
                    "metadata": chunk.get("metadata", {})
                }
            )
            points.append(point)
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        print(f"Inserted {len(points)} chunks into collection")
    
    def search(self, query: str, top_k: Optional[int] = None) -> List[RetrievedChunk]:
        k = top_k or self.top_k
        
        query_embedding = self.embedder.encode_queries([query])[0]
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=("text", query_embedding.tolist()),
            limit=k
        )
        
        retrieved = []
        for result in results:
            retrieved.append(RetrievedChunk(
                chunk_id=result.payload["chunk_id"],
                text=result.payload["text"],
                policy_id=result.payload["policy_id"],
                policy_type=result.payload["policy_type"],
                score=result.score,
                metadata=result.payload.get("metadata", {})
            ))
        
        return retrieved
    
    def search_with_filter(self, query: str, policy_type: Optional[str] = None, 
                          top_k: Optional[int] = None) -> List[RetrievedChunk]:
        k = top_k or self.top_k
        
        query_embedding = self.embedder.encode_queries([query])[0]
        
        filter_condition = None
        if policy_type:
            filter_condition = Filter(
                must=[
                    {"key": "policy_type", "match": {"value": policy_type}}
                ]
            )
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=("text", query_embedding.tolist()),
            query_filter=filter_condition,
            limit=k
        )
        
        retrieved = []
        for result in results:
            retrieved.append(RetrievedChunk(
                chunk_id=result.payload["chunk_id"],
                text=result.payload["text"],
                policy_id=result.payload["policy_id"],
                policy_type=result.payload["policy_type"],
                score=result.score,
                metadata=result.payload.get("metadata", {})
            ))
        
        return retrieved
    
    def get_collection_info(self) -> Dict[str, Any]:
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            return {
                "name": info.name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            return {"error": str(e)}
    
    def delete_collection(self):
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            print(f"Deleted collection: {self.collection_name}")
        except Exception as e:
            print(f"Error deleting collection: {e}")


def load_chunks(path: str = "data/processed/chunks.jsonl") -> List[Dict[str, Any]]:
    chunks = []
    file_path = Path(path)
    
    if not file_path.exists():
        file_path = Path(__file__).parent.parent.parent / path
    
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    
    return chunks


def load_embeddings(path: str = "data/processed/embeddings.npy") -> np.ndarray:
    file_path = Path(path)
    
    if not file_path.exists():
        file_path = Path(__file__).parent.parent.parent / path
    
    return np.load(file_path)


def main():
    config = get_config()
    store = VectorStore(config)
    
    chunks = load_chunks()
    embeddings = load_embeddings()
    
    print(f"Loaded {len(chunks)} chunks and {embeddings.shape[0]} embeddings")
    
    store.insert_chunks(chunks, embeddings)
    
    query = "What is the pre-existing conditions waiting period?"
    results = store.search(query)
    
    print(f"\nQuery: {query}")
    print(f"Retrieved {len(results)} chunks:")
    for i, result in enumerate(results[:3]):
        print(f"\n--- Result {i + 1} (score: {result.score:.4f}) ---")
        print(f"Policy: {result.policy_id}, Type: {result.policy_type}")
        print(f"Text: {result.text[:150]}...")


if __name__ == "__main__":
    main()
