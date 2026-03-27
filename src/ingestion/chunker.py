import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.config import get_config


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    policy_id: str
    policy_type: str
    source: str
    chunk_index: int
    total_chunks: int
    metadata: Dict[str, Any]


class DocumentChunker:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.chunk_size = self.config.rag.chunk_size
        self.chunk_overlap = self.config.rag.chunk_overlap
    
    def chunk_text(self, text: str, policy_id: str, policy_type: str, source: str) -> List[DocumentChunk]:
        chunks = []
        
        text = self._clean_text(text)
        
        sections = self._split_by_sections(text)
        
        chunk_index = 0
        for section in sections:
            if len(section) <= self.chunk_size:
                if section.strip():
                    chunk = DocumentChunk(
                        chunk_id=f"{policy_id}_chunk_{chunk_index}",
                        text=section.strip(),
                        policy_id=policy_id,
                        policy_type=policy_type,
                        source=source,
                        chunk_index=chunk_index,
                        total_chunks=0,
                        metadata={"section_type": "full"}
                    )
                    chunks.append(chunk)
                    chunk_index += 1
            else:
                sub_chunks = self._chunk_by_size(section, policy_id, chunk_index, policy_type, source)
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
        
        for i, chunk in enumerate(chunks):
            chunk.total_chunks = len(chunks)
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text
    
    def _split_by_sections(self, text: str) -> List[str]:
        section_pattern = r'\n(SECTION \d+:|Article \d+:|Chapter \d+:)'
        parts = re.split(section_pattern, text)
        
        sections = []
        for i in range(1, len(parts), 2):
            header = parts[i]
            content = parts[i + 1] if i + 1 < len(parts) else ""
            sections.append(f"{header} {content}".strip())
        
        if not sections and parts:
            sections = [p for p in parts if p.strip()]
        
        if not sections:
            sections = [text]
        
        return sections
    
    def _chunk_by_size(self, text: str, policy_id: str, start_index: int, 
                       policy_type: str, source: str) -> List[DocumentChunk]:
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        chunk_index = start_index
        
        for word in words:
            word_length = len(word) + 1
            if current_length + word_length > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                if current_length >= self.chunk_size * 0.3:
                    chunk = DocumentChunk(
                        chunk_id=f"{policy_id}_chunk_{chunk_index}",
                        text=chunk_text,
                        policy_id=policy_id,
                        policy_type=policy_type,
                        source=source,
                        chunk_index=chunk_index,
                        total_chunks=0,
                        metadata={"section_type": "partial"}
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                overlap_words = current_chunk[-self.chunk_overlap // 5:]
                current_chunk = overlap_words + [word]
                current_length = sum(len(w) + 1 for w in current_chunk)
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunk = DocumentChunk(
                chunk_id=f"{policy_id}_chunk_{chunk_index}",
                text=chunk_text,
                policy_id=policy_id,
                policy_type=policy_type,
                source=source,
                chunk_index=chunk_index,
                total_chunks=0,
                metadata={"section_type": "partial"}
            )
            chunks.append(chunk)
        
        return chunks
    
    def process_documents(self, documents: List[Dict[str, Any]]) -> List[DocumentChunk]:
        all_chunks = []
        
        for doc in documents:
            content = doc.get("content", "")
            if not content:
                continue
            
            chunks = self.chunk_text(
                text=content,
                policy_id=doc.get("policy_id", "unknown"),
                policy_type=doc.get("type", "unknown"),
                source=doc.get("source", "unknown")
            )
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def save_chunks(self, chunks: List[DocumentChunk], output_path: str):
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            for chunk in chunks:
                chunk_dict = {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "policy_id": chunk.policy_id,
                    "policy_type": chunk.policy_type,
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": chunk.total_chunks,
                    "metadata": chunk.metadata
                }
                f.write(json.dumps(chunk_dict) + '\n')


def load_raw_documents(path: str = "data/raw/policy_documents.jsonl") -> List[Dict[str, Any]]:
    documents = []
    file_path = Path(path)
    
    if not file_path.exists():
        file_path = Path(__file__).parent.parent.parent / path
    
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                documents.append(json.loads(line))
    
    return documents


def main():
    config = get_config()
    chunker = DocumentChunker(config)
    
    documents = load_raw_documents()
    print(f"Loaded {len(documents)} documents")
    
    chunks = chunker.process_documents(documents)
    print(f"Created {len(chunks)} chunks")
    
    output_path = Path(str(config.data.processed_path)) / "chunks.jsonl"
    chunker.save_chunks(chunks, str(output_path))
    print(f"Saved chunks to {output_path}")
    
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n--- Chunk {i} ---")
        print(f"ID: {chunk.chunk_id}")
        print(f"Text (first 100 chars): {chunk.text[:100]}...")


if __name__ == "__main__":
    main()
