import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

from sentence_transformers import SentenceTransformer

from src.config import get_config


class EmbeddingGenerator:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.model_name = self.config.rag.embedding_model
        self._model = None
    
    @property
    def model(self):
        if self._model is None:
            print(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    def encode(self, texts: List[str], batch_size: int = 32, 
               normalize: bool = True) -> np.ndarray:
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize,
            show_progress_bar=True
        )
        return embeddings
    
    def encode_queries(self, queries: List[str]) -> np.ndarray:
        return self.encode(queries)
    
    def encode_documents(self, documents: List[str]) -> np.ndarray:
        return self.encode(documents)
    
    def get_embedding_dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()


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


def generate_embeddings(chunks: List[Dict[str, Any]], output_path: str):
    generator = EmbeddingGenerator()
    
    texts = [chunk["text"] for chunk in chunks]
    
    print(f"Generating embeddings for {len(texts)} chunks...")
    embeddings = generator.encode_documents(texts)
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'wb') as f:
        np.save(f, embeddings)
    
    print(f"Saved embeddings to {output_file}")
    return embeddings


def main():
    config = get_config()
    generator = EmbeddingGenerator(config)
    
    chunks = load_chunks()
    print(f"Loaded {len(chunks)} chunks")
    
    output_path = Path(str(config.data.processed_path)) / "embeddings.npy"
    embeddings = generate_embeddings(chunks, str(output_path))
    
    print(f"Embedding dimension: {embeddings.shape[1]}")
    print(f"Number of embeddings: {embeddings.shape[0]}")


if __name__ == "__main__":
    main()
