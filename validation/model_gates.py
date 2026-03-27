import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from src.config import get_config


@dataclass
class ValidationMetrics:
    faithfulness: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    pii_leak_count: int = 0
    retrieval_precision: float = 0.0
    retrieval_recall: float = 0.0
    timestamp: str = ""


class RAGPromotionGate:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.validation = self.config.validation
    
    def validate(self, metrics: ValidationMetrics) -> Dict[str, Any]:
        gates = {
            "faithfulness": metrics.faithfulness >= self.validation.faithfulness_threshold,
            "precision": metrics.precision >= self.validation.precision_threshold,
            "recall": metrics.recall >= self.validation.recall_threshold,
            "pii_zero_tolerance": metrics.pii_leak_count == self.validation.pii_leak_tolerance,
            "latency_p99": metrics.latency_p99_ms <= self.validation.p99_sla_ms,
            "latency_p95": metrics.latency_p95_ms <= self.validation.p95_sla_ms,
            "retrieval_precision": metrics.retrieval_precision >= self.validation.precision_threshold,
        }
        
        all_passed = all(gates.values())
        
        failed_gates = [gate for gate, passed in gates.items() if not passed]
        
        return {
            "passed": all_passed,
            "gates": gates,
            "failed_gates": failed_gates,
            "metrics": {
                "faithfulness": metrics.faithfulness,
                "precision": metrics.precision,
                "recall": metrics.recall,
                "pii_leak_count": metrics.pii_leak_count,
                "latency_p99_ms": metrics.latency_p99_ms,
                "latency_p95_ms": metrics.latency_p95_ms,
            },
            "thresholds": {
                "faithfulness": self.validation.faithfulness_threshold,
                "precision": self.validation.precision_threshold,
                "recall": self.validation.recall_threshold,
                "p99_sla_ms": self.validation.p99_sla_ms,
                "p95_sla_ms": self.validation.p95_sla_ms,
                "pii_leak_tolerance": self.validation.pii_leak_tolerance,
            }
        }
    
    def alert_compliance(self, metrics: ValidationMetrics):
        print("=" * 60)
        print("⚠️  COMPLIANCE ALERT: PII LEAK DETECTED")
        print("=" * 60)
        print(f"Timestamp: {metrics.timestamp}")
        print(f"PII Leaks Found: {metrics.pii_leak_count}")
        print("This is a zero-tolerance gate failure.")
        print("Immediate investigation required.")
        print("=" * 60)


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


def compute_latency_percentiles(latencies: List[float]) -> Dict[str, float]:
    if not latencies:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
    
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)
    
    p50_idx = int(n * 0.50)
    p95_idx = int(n * 0.95)
    p99_idx = int(n * 0.99)
    
    return {
        "p50": sorted_latencies[p50_idx] if p50_idx < n else sorted_latencies[-1],
        "p95": sorted_latencies[p95_idx] if p95_idx < n else sorted_latencies[-1],
        "p99": sorted_latencies[p99_idx] if p99_idx < n else sorted_latencies[-1],
    }


from pathlib import Path


def main():
    config = get_config()
    gate = RAGPromotionGate(config)
    
    metrics = ValidationMetrics(
        faithfulness=0.87,
        precision=0.89,
        recall=0.86,
        latency_p50_ms=450,
        latency_p95_ms=2200,
        latency_p99_ms=2800,
        pii_leak_count=0,
        retrieval_precision=0.90,
        retrieval_recall=0.85,
        timestamp=datetime.now().isoformat()
    )
    
    result = gate.validate(metrics)
    
    print("Validation Result:")
    print("=" * 40)
    print(f"Passed: {result['passed']}")
    print(f"\nGate Results:")
    for gate_name, passed in result['gates'].items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {gate_name}: {status}")
    
    if result['failed_gates']:
        print(f"\nFailed Gates: {result['failed_gates']}")


if __name__ == "__main__":
    main()
