import sys
from datetime import datetime, timedelta
import json
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config
from monitoring.latency_monitor import LatencyMonitor, DriftDetector


default_args = {
    'owner': 'mlops',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def check_latency_sla():
    """Check latency SLA compliance."""
    monitor = LatencyMonitor()
    
    sla_status = monitor.check_sla()
    
    print(f"SLA Status: {json.dumps(sla_status, indent=2)}")
    
    output_path = Path("monitoring/sla_status.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(sla_status, f, indent=2)
    
    if sla_status.get('sla_violated'):
        print(f"WARNING: SLA violated! P99: {sla_status['p99_ms']}ms")
        return {"status": "violated", "details": sla_status}
    
    return {"status": "ok", "details": sla_status}


def check_drift():
    """Check for query distribution drift."""
    detector = DriftDetector()
    
    reference_dist = {
        "health": 0.3,
        "auto": 0.25,
        "home": 0.25,
        "life": 0.1,
        "other": 0.1
    }
    
    import random
    queries = [
        "health coverage", "auto insurance", "homeowners policy", 
        "term life", "deductible", "pre-existing conditions"
    ]
    for _ in range(100):
        detector.record_query(random.choice(queries))
    
    drift_result = detector.check_drift(reference_dist)
    
    print(f"Drift Check: {json.dumps(drift_result, indent=2)}")
    
    output_path = Path("monitoring/drift_status.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(drift_result, f, indent=2)
    
    return drift_result


def run_monitoring_dag():
    """Main monitoring task."""
    from src.rag_pipeline.pipeline import RAGPipeline
    
    pipeline = RAGPipeline()
    pipeline.initialize()
    
    monitor = LatencyMonitor()
    detector = DriftDetector()
    
    test_queries = [
        "What is the pre-existing conditions waiting period?",
        "What is the bodily injury liability limit?",
        "What is the personal property coverage?",
        "What is the maximum coverage amount?",
    ]
    
    for query in test_queries:
        result = pipeline.query(query)
        monitor.record_latency(result.latency_ms, query)
        detector.record_query(query)
    
    stats = monitor.get_stats()
    
    print(f"Monitoring stats: {json.dumps(stats, indent=2)}")
    
    return stats


def generate_report():
    """Generate monitoring report."""
    sla_path = Path("monitoring/sla_status.json")
    drift_path = Path("monitoring/drift_status.json")
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "sla": {},
        "drift": {}
    }
    
    if sla_path.exists():
        with open(sla_path, 'r') as f:
            report["sla"] = json.load(f)
    
    if drift_path.exists():
        with open(drift_path, 'r') as f:
            report["drift"] = json.load(f)
    
    output_path = Path("monitoring/report.json")
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Report generated: {output_path}")
    return report


with DAG(
    'rag_monitoring_dag',
    default_args=default_args,
    description='Hourly RAG monitoring - latency, drift, SLA',
    schedule_interval='0 * * * *',
    catchup=False,
    tags=['rag', 'monitoring', 'mlops'],
) as dag:
    
    start = BashOperator(
        task_id='start',
        bash_command='echo "Starting RAG monitoring DAG"'
    )
    
    run_monitoring = PythonOperator(
        task_id='run_monitoring',
        python_callable=run_monitoring_dag,
    )
    
    check_sla = PythonOperator(
        task_id='check_latency_sla',
        python_callable=check_latency_sla,
    )
    
    check_drift_task = PythonOperator(
        task_id='check_drift',
        python_callable=check_drift,
    )
    
    generate_report_task = PythonOperator(
        task_id='generate_report',
        python_callable=generate_report,
    )
    
    end = BashOperator(
        task_id='end',
        bash_command='echo "Monitoring DAG complete"'
    )
    
    start >> run_monitoring >> [check_sla, check_drift_task] >> generate_report_task >> end
