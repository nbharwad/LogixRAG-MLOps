import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

import mlflow
from mlflow.tracking import MlflowClient

from src.config import get_config


class ExperimentTracker:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.tracking_uri = self.config.mlflow.tracking_uri
        self.experiment_name = self.config.mlflow.experiment_name
        self._client = None
        self._setup_mlflow()
    
    def _setup_mlflow(self):
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment_name)
        self._client = MlflowClient()
    
    def start_run(self, run_name: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
        return mlflow.start_run(run_name=run_name, tags=tags)
    
    def log_params(self, params: Dict[str, Any]):
        mlflow.log_params(params)
    
    def log_metrics(self, metrics: Dict[str, float]):
        mlflow.log_metrics(metrics)
    
    def log_metric(self, key: str, value: float):
        mlflow.log_metric(mlflow.entities.Metric(key, value, 0, 0))
    
    def log_text(self, text: str, artifact_file: str):
        mlflow.log_text(text, artifact_file)
    
    def log_json(self, data: Dict, artifact_file: str):
        mlflow.log_dict(data, artifact_file)
    
    def register_model(self, model_name: str, model_uri: Optional[str] = None):
        if model_uri is None:
            model_uri = mlflow.get_artifact_uri("model")
        
        try:
            self._client.register_model(
                name=model_name,
                source=model_uri
            )
            print(f"Registered model: {model_name}")
        except Exception as e:
            print(f"Model registration skipped: {e}")
    
    def transition_model_stage(self, model_name: str, version: int, stage: str):
        try:
            self._client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage
            )
            print(f"Transitioned {model_name} v{version} to {stage}")
        except Exception as e:
            print(f"Stage transition skipped: {e}")
    
    def get_experiment(self):
        return mlflow.get_experiment_by_name(self.experiment_name)
    
    def list_runs(self, max_results: int = 100):
        experiment = self.get_experiment()
        if experiment:
            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                max_results=max_results
            )
            return runs
        return []


def log_rag_run(
    run_name: str,
    config: Dict[str, Any],
    metrics: Dict[str, float],
    artifacts: Optional[Dict[str, str]] = None,
    model_name: Optional[str] = None
):
    tracker = ExperimentTracker()
    
    with tracker.start_run(run_name=run_name) as run:
        tracker.log_params({
            f"rag.{k}": v for k, v in config.get("rag", {}).items()
        })
        tracker.log_params({
            f"llm.{k}": v for k, v in config.get("llm", {}).items()
        })
        
        tracker.log_metrics(metrics)
        
        if artifacts:
            for name, path in artifacts.items():
                if Path(path).exists():
                    mlflow.log_artifact(path, artifact_path=name)
        
        if model_name:
            tracker.register_model(model_name)


def main():
    config = get_config()
    tracker = ExperimentTracker(config)
    
    print(f"MLflow Tracking URI: {tracker.tracking_uri}")
    print(f"Experiment: {tracker.experiment_name}")
    
    with tracker.start_run(run_name="test_run") as run:
        tracker.log_params({"test_param": 1})
        tracker.log_metrics({
            "faithfulness": 0.87,
            "precision": 0.89,
            "recall": 0.86
        })
        
        print(f"Run ID: {run.info.run_id}")


if __name__ == "__main__":
    main()
