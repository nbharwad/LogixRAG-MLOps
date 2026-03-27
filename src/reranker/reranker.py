import json
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

from src.config import get_config


class Reranker:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.model_name = self.config.rag.reranker_model
        self._model = None
    
    @property
    def model(self):
        if self._model is None:
            print(f"Loading reranker model: {self.model_name}")
            from FlagEmbedding import BGEM3FlagModel
            self._model = BGEM3FlagModel(self.model_name, use_fp16=True)
        return self._model
    
    def rerank(self, query: str, documents: List[str], top_k: int = None) -> List[Dict[str, Any]]:
        if top_k is None:
            top_k = self.config.rag.top_k
        
        if not documents:
            return []
        
        if "bge" in self.model_name.lower():
            results = self.model.compute_score(
                query=query,
                sentences=documents,
                batch_size=len(documents),
                show_progress_bar=True
            )
            
            if isinstance(results, list):
                scored_docs = [
                    {"text": doc, "score": score} 
                    for doc, score in zip(documents, results)
                ]
            else:
                scored_docs = [{"text": documents[0], "score": results}]
            
            scored_docs.sort(key=lambda x: x["score"], reverse=True)
            return scored_docs[:top_k]
        
        return [{"text": doc, "score": 1.0} for doc in documents[:top_k]]


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


def main():
    config = get_config()
    reranker = Reranker(config)
    
    query = "What is the waiting period for pre-existing conditions?"
    documents = [
        "INDIVIDUAL HEALTH INSURANCE POLICY - Pre-existing conditions waiting period: 12 months",
        "Auto insurance covers vehicle damage and liability",
        "Home insurance covers dwelling and personal property",
        "Life insurance provides death benefit to beneficiaries",
        "Group health insurance requires 75% participation"
    ]
    
    results = reranker.rerank(query, documents, top_k=3)
    
    print(f"Query: {query}")
    print(f"\nReranked results:")
    for i, result in enumerate(results):
        print(f"{i + 1}. Score: {result['score']:.4f}")
        print(f"   Text: {result['text'][:80]}...")


if __name__ == "__main__":
    main()
