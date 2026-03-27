import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from collections import deque

from src.config import get_config


@dataclass
class LatencyMetric:
    timestamp: str
    latency_ms: float
    query: str


class LatencyMonitor:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.sla_ms = self.config.monitoring.latency_check_interval_sec
        self.alert_webhook = self.config.monitoring.alert_webhook
        self._recent_latencies = deque(maxlen=1000)
        self._start_time = time.time()
    
    def record_latency(self, latency_ms: float, query: str = ""):
        metric = LatencyMetric(
            timestamp=datetime.now().isoformat(),
            latency_ms=latency_ms,
            query=query
        )
        self._recent_latencies.append(metric)
    
    def get_percentiles(self) -> Dict[str, float]:
        if not self._recent_latencies:
            return {"p50": 0, "p95": 0, "p99": 0, "p999": 0}
        
        latencies = sorted([m.latency_ms for m in self._recent_latencies])
        n = len(latencies)
        
        return {
            "p50": latencies[int(n * 0.50)],
            "p95": latencies[int(n * 0.95)],
            "p99": latencies[min(int(n * 0.99), n - 1)],
            "p999": latencies[min(int(n * 0.999), n - 1)],
            "avg": sum(latencies) / n,
            "max": max(latencies),
            "min": min(latencies),
        }
    
    def check_sla(self) -> Dict[str, Any]:
        percentiles = self.get_percentiles()
        
        p99_violation = percentiles["p99"] > self.config.validation.p99_sla_ms
        p95_violation = percentiles["p95"] > self.config.validation.p95_sla_ms
        
        return {
            "sla_violated": p99_violation or p95_violation,
            "p99_ms": percentiles["p99"],
            "p95_ms": percentiles["p95"],
            "p99_threshold": self.config.validation.p99_sla_ms,
            "p95_threshold": self.config.validation.p95_sla_ms,
            "total_requests": len(self._recent_latencies),
            "uptime_seconds": time.time() - self._start_time
        }
    
    def send_alert(self, message: str):
        print(f"ALERT: {message}")
        
        if self.alert_webhook:
            try:
                import httpx
                httpx.post(self.alert_webhook, json={"text": message})
            except Exception as e:
                print(f"Failed to send webhook alert: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        percentiles = self.get_percentiles()
        sla_status = self.check_sla()
        
        return {
            "percentiles": percentiles,
            "sla_status": sla_status,
            "recent_requests": len(self._recent_latencies)
        }


class DriftDetector:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.drift_threshold = self.config.monitoring.drift_threshold
        self._query_distribution = {}
        self._total_queries = 0
    
    def record_query(self, query: str):
        self._total_queries += 1
        
        query_type = self.classify_query(query)
        
        if query_type not in self._query_distribution:
            self._query_distribution[query_type] = 0
        self._query_distribution[query_type] += 1
    
    def classify_query(self, query: str) -> str:
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["pre-existing", "coverage", "deductible", "health"]):
            return "health"
        elif any(word in query_lower for word in ["liability", "collision", "deductible", "auto", "vehicle"]):
            return "auto"
        elif any(word in query_lower for word in ["dwelling", "property", "home", "homeowners"]):
            return "home"
        elif any(word in query_lower for word in ["term", "life", "beneficiary", "death"]):
            return "life"
        else:
            return "other"
    
    def get_distribution(self) -> Dict[str, float]:
        if self._total_queries == 0:
            return {}
        
        return {
            query_type: count / self._total_queries 
            for query_type, count in self._query_distribution.items()
        }
    
    def check_drift(self, reference_distribution: Dict[str, float]) -> Dict[str, Any]:
        current_dist = self.get_distribution()
        
        if not reference_distribution or not current_dist:
            return {"drift_detected": False, "message": "Insufficient data"}
        
        all_types = set(reference_distribution.keys()) | set(current_dist.keys())
        
        drift_scores = {}
        for qtype in all_types:
            ref = reference_distribution.get(qtype, 0)
            curr = current_dist.get(qtype, 0)
            drift_scores[qtype] = abs(curr - ref)
        
        max_drift = max(drift_scores.values()) if drift_scores else 0
        
        return {
            "drift_detected": max_drift > self.drift_threshold,
            "max_drift": max_drift,
            "threshold": self.drift_threshold,
            "drift_by_type": drift_scores,
            "current_distribution": current_dist,
            "reference_distribution": reference_distribution,
            "total_queries": self._total_queries
        }


def main():
    monitor = LatencyMonitor()
    
    for i in range(100):
        latency = 100 + (i % 50) * 10
        monitor.record_latency(float(latency), f"query_{i}")
    
    stats = monitor.get_stats()
    print("Latency Monitor Stats:")
    print(f"  P50: {stats['percentiles']['p50']:.2f}ms")
    print(f"  P95: {stats['percentiles']['p95']:.2f}ms")
    print(f"  P99: {stats['percentiles']['p99']:.2f}ms")
    
    sla = monitor.check_sla()
    print(f"\nSLA Status:")
    print(f"  Violated: {sla['sla_violated']}")
    print(f"  P99: {sla['p99_ms']:.2f}ms (limit: {sla['p99_threshold']}ms)")


if __name__ == "__main__":
    main()
