import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RAGConfig(BaseModel):
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    reranker_model: str = "BAAI/bge-reranker-base"
    vector_db: str = "qdrant"
    collection_name: str = "insurance_policies"


class LLMConfig(BaseModel):
    provider: str = "ollama"
    model: str = "llama3.2:3b"
    temperature: float = 0.1
    max_tokens: int = 2048


class ValidationConfig(BaseModel):
    faithfulness_threshold: float = 0.85
    precision_threshold: float = 0.88
    recall_threshold: float = 0.85
    latency_sla_ms: int = 3000
    p99_sla_ms: int = 3000
    p95_sla_ms: int = 2500
    pii_leak_tolerance: int = 0


class ModelConfig(BaseModel):
    random_state: int = 42
    eval_batch_size: int = 32


class DataConfig(BaseModel):
    raw_path: str = "data/raw"
    processed_path: str = "data/processed"
    eval_path: str = "data/eval"


class FeatureStoreConfig(BaseModel):
    provider: str = "feast"
    online_store: str = "sqlite"
    offline_store: str = "sqlite"
    db_path: str = "features/feature_store/feast.db"


class MLflowConfig(BaseModel):
    tracking_uri: str = "http://localhost:5000"
    experiment_name: str = "LogixRAG-MLOps"
    registry_uri: str = "http://localhost:5000"


class DVCConfig(BaseModel):
    remote: str = "dagshub"
    repro_cache: str = ".dvc/cache"


class MonitoringConfig(BaseModel):
    drift_threshold: float = 0.05
    latency_check_interval_sec: int = 60
    alert_webhook: str = ""


class AirflowConfig(BaseModel):
    dags_folder: str = "dags"
    schedule_interval: str = "0 */6 * * *"


class AppConfig(BaseModel):
    rag: RAGConfig
    llm: LLMConfig
    validation: ValidationConfig
    model: ModelConfig
    data: DataConfig
    feature_store: FeatureStoreConfig
    mlflow: MLflowConfig
    dvc: DVCConfig
    monitoring: MonitoringConfig
    airflow: AirflowConfig


_config: Optional[AppConfig] = None


def load_config(config_path: str = "config.yaml") -> AppConfig:
    global _config
    if _config is None:
        path = Path(config_path)
        if not path.exists():
            path = Path(__file__).parent.parent / config_path
        
        with open(path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        _config = AppConfig(**config_dict)
    return _config


def get_config() -> AppConfig:
    if _config is None:
        return load_config()
    return _config


def reset_config() -> None:
    global _config
    _config = None
