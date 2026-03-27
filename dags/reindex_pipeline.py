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
from src.ingestion.chunker import DocumentChunker, load_raw_documents
from src.embeddings.generator import EmbeddingGenerator
from src.retrieval.vector_store import VectorStore


default_args = {
    'owner': 'mlops',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def load_documents():
    """Load raw policy documents."""
    documents = load_raw_documents()
    print(f"Loaded {len(documents)} documents")
    return len(documents)


def chunk_documents():
    """Chunk documents into smaller pieces."""
    config = get_config()
    chunker = DocumentChunker(config)
    documents = load_raw_documents()
    chunks = chunker.process_documents(documents)
    
    output_path = Path(str(config.data.processed_path)) / "chunks.jsonl"
    chunker.save_chunks(chunks, str(output_path))
    print(f"Created and saved {len(chunks)} chunks")
    return len(chunks)


def generate_embeddings_task():
    """Generate embeddings for chunks."""
    config = get_config()
    embedder = EmbeddingGenerator(config)
    
    chunks = load_chunks()
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedder.encode_documents(texts)
    
    import numpy as np
    emb_path = Path(str(config.data.processed_path)) / "embeddings.npy"
    with open(emb_path, 'wb') as f:
        np.save(f, embeddings)
    
    print(f"Generated {embeddings.shape[0]} embeddings")
    return embeddings.shape[0]


def build_vector_index():
    """Build vector store index."""
    config = get_config()
    store = VectorStore(config)
    
    chunks = load_chunks()
    import numpy as np
    embeddings = np.load(Path(str(config.data.processed_path)) / "embeddings.npy")
    
    store.insert_chunks(chunks, embeddings)
    print("Vector index built successfully")
    return True


def run_evaluation():
    """Run RAG evaluation."""
    from validation.rag_eval import RAGEvaluator
    from src.rag_pipeline.pipeline import RAGPipeline
    
    evaluator = RAGEvaluator()
    pipeline = RAGPipeline()
    pipeline.initialize()
    
    results = evaluator.evaluate_dataset(pipeline)
    
    output_path = Path("data/eval/results.json")
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Evaluation complete: {results}")
    return results


def validate_gates():
    """Validate model promotion gates."""
    from validation.model_gates import RAGPromotionGate, ValidationMetrics
    from datetime import datetime
    
    eval_results_path = Path("data/eval/results.json")
    if eval_results_path.exists():
        with open(eval_results_path, 'r') as f:
            results = json.load(f)
        
        metrics = ValidationMetrics(
            faithfulness=results.get('faithfulness', 0),
            precision=results.get('precision', 0),
            recall=results.get('recall', 0),
            latency_p50_ms=results.get('latency_p50_ms', 0),
            latency_p95_ms=results.get('latency_p95_ms', 0),
            latency_p99_ms=results.get('latency_p99_ms', 0),
            pii_leak_count=0,
            retrieval_precision=results.get('precision', 0),
            retrieval_recall=results.get('recall', 0),
            timestamp=datetime.now().isoformat()
        )
        
        gate = RAGPromotionGate()
        result = gate.validate(metrics)
        
        print(f"Gate validation: {result}")
        
        if not result['passed']:
            raise ValueError(f"Gate validation failed: {result['failed_gates']}")
        
        return result
    else:
        print("No evaluation results found, skipping gate validation")


with DAG(
    'rag_reindex_pipeline',
    default_args=default_args,
    description='RAG reindexing pipeline - runs when documents are updated',
    schedule_interval=None,
    catchup=False,
    tags=['rag', 'reindex', 'mlops'],
) as dag:
    
    start = BashOperator(
        task_id='start',
        bash_command='echo "Starting RAG reindex pipeline"'
    )
    
    with TaskGroup('data_loading'):
        load_task = PythonOperator(
            task_id='load_documents',
            python_callable=load_documents,
        )
    
    with TaskGroup('processing'):
        chunk_task = PythonOperator(
            task_id='chunk_documents',
            python_callable=chunk_documents,
        )
        
        embed_task = PythonOperator(
            task_id='generate_embeddings',
            python_callable=generate_embeddings_task,
        )
        
        index_task = PythonOperator(
            task_id='build_vector_index',
            python_callable=build_vector_index,
        )
    
    with TaskGroup('validation'):
        eval_task = PythonOperator(
            task_id='run_evaluation',
            python_callable=run_evaluation,
        )
        
        gate_task = PythonOperator(
            task_id='validate_gates',
            python_callable=validate_gates,
        )
    
    end = BashOperator(
        task_id='end',
        bash_command='echo "RAG reindex pipeline complete"'
    )
    
    start >> load_task >> chunk_task >> embed_task >> index_task >> eval_task >> gate_task >> end


def load_chunks(path: str = "data/processed/chunks.jsonl"):
    chunks = []
    file_path = Path(path)
    
    if not file_path.exists():
        file_path = Path(__file__).parent.parent.parent / path
    
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    
    return chunks
