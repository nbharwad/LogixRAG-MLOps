import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from dataclasses import dataclass

from src.config import get_config


@dataclass
class RAGEvaluationResult:
    question: str
    answer: str
    expected_answer: str
    context_policy_id: str
    faithfulness: float
    context_precision: float
    context_recall: float
    answer_relevance: float
    latency_ms: float


def load_eval_pairs(path: str = "data/eval/qa_pairs.jsonl") -> List[Dict[str, Any]]:
    eval_pairs = []
    file_path = Path(path)
    
    if not file_path.exists():
        file_path = Path(__file__).parent.parent.parent / path
    
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                eval_pairs.append(json.loads(line))
    
    return eval_pairs


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


class RAGEvaluator:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.eval_pairs = None
        self.chunks = None
    
    def load_data(self):
        self.eval_pairs = load_eval_pairs()
        self.chunks = load_chunks()
        print(f"Loaded {len(self.eval_pairs)} eval pairs and {len(self.chunks)} chunks")
    
    def evaluate_faithfulness(self, answer: str, contexts: List[str]) -> float:
        answer_lower = answer.lower()
        context_text = " ".join(contexts).lower()
        
        answer_words = set(answer_lower.split())
        context_words = set(context_text.split())
        
        if not answer_words:
            return 0.0
        
        matching_words = answer_words & context_words
        return len(matching_words) / len(answer_words)
    
    def evaluate_context_precision(self, retrieved_chunks: List[Dict], 
                                   expected_policy_id: str) -> float:
        if not retrieved_chunks:
            return 0.0
        
        relevant = sum(1 for chunk in retrieved_chunks 
                      if chunk.get("policy_id") == expected_policy_id)
        return relevant / len(retrieved_chunks)
    
    def evaluate_context_recall(self, retrieved_chunks: List[Dict], 
                               expected_policy_id: str) -> float:
        if not retrieved_chunks:
            return 0.0
        
        relevant = sum(1 for chunk in retrieved_chunks 
                      if chunk.get("policy_id") == expected_policy_id)
        total_relevant = 1
        
        return min(relevant / total_relevant, 1.0)
    
    def evaluate_answer_relevance(self, answer: str, question: str) -> float:
        answer_words = set(answer.lower().split())
        question_words = set(question.lower().split())
        
        if not answer_words:
            return 0.0
        
        overlap = len(answer_words & question_words)
        return min(overlap / len(question_words), 1.0)
    
    def evaluate_single(self, question: str, answer: str, 
                       retrieved_chunks: List[Dict], expected_policy_id: str,
                       latency_ms: float = 0.0) -> RAGEvaluationResult:
        contexts = [chunk.get("text", "") for chunk in retrieved_chunks]
        
        faithfulness = self.evaluate_faithfulness(answer, contexts)
        context_precision = self.evaluate_context_precision(
            retrieved_chunks, expected_policy_id
        )
        context_recall = self.evaluate_context_recall(
            retrieved_chunks, expected_policy_id
        )
        answer_relevance = self.evaluate_answer_relevance(answer, question)
        
        return RAGEvaluationResult(
            question=question,
            answer=answer,
            expected_answer="",
            context_policy_id=expected_policy_id,
            faithfulness=faithfulness,
            context_precision=context_precision,
            context_recall=context_recall,
            answer_relevance=answer_relevance,
            latency_ms=latency_ms
        )
    
    def evaluate_dataset(self, pipeline) -> Dict[str, Any]:
        if not self.eval_pairs:
            self.load_data()
        
        results = []
        latencies = []
        
        for eval_pair in self.eval_pairs:
            question = eval_pair["question"]
            expected_policy_id = eval_pair["context_policy_id"]
            
            from src.rag_pipeline.pipeline import RAGResponse
            response = pipeline.query(question, mask_pii=True)
            
            result = self.evaluate_single(
                question=question,
                answer=response.answer,
                retrieved_chunks=[
                    {"text": s["text"], "policy_id": s["policy_id"]} 
                    for s in response.sources
                ],
                expected_policy_id=expected_policy_id,
                latency_ms=response.latency_ms
            )
            results.append(result)
            latencies.append(response.latency_ms)
        
        avg_faithfulness = np.mean([r.faithfulness for r in results])
        avg_precision = np.mean([r.context_precision for r in results])
        avg_recall = np.mean([r.context_recall for r in results])
        avg_relevance = np.mean([r.answer_relevance for r in results])
        
        sorted_latencies = sorted(latencies)
        p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)]
        p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
        p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]
        
        return {
            "faithfulness": avg_faithfulness,
            "precision": avg_precision,
            "recall": avg_recall,
            "answer_relevance": avg_relevance,
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
            "latency_p99_ms": p99,
            "total_evaluations": len(results),
            "results": [
                {
                    "question": r.question,
                    "faithfulness": r.faithfulness,
                    "context_precision": r.context_precision,
                    "context_recall": r.context_recall
                }
                for r in results
            ]
        }


def main():
    from src.rag_pipeline.pipeline import RAGPipeline
    
    config = get_config()
    evaluator = RAGEvaluator(config)
    evaluator.load_data()
    
    print("RAG Evaluation Complete (simulation)")
    print("=" * 50)
    print("Note: Run pipeline first to get actual metrics")


if __name__ == "__main__":
    main()
