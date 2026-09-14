# Reproducibility Guide

## Setup
```bash
git clone https://github.com/arraimal70-code/RAG-Pipeline.git
cd RAG-Pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add OPENAI_API_KEY
```

## Running Experiments
```bash
# 1. Add documents
mkdir -p data/documents && cp *.pdf data/documents/

# 2. Ingest
python -m src.pipeline ingest

# 3. Run experiments
python experiments/runner.py

# 4. View results
cat experiments/results/COMPARISON.md
```

## Docker
```bash
docker build -t rag-pipeline .
docker run -p 8000:8000 --env-file .env rag-pipeline
```

## Result Format
Each experiment produces JSON with:
- experiment_id, name, hypothesis, method
- config_snapshot (full configuration at time of run)
- dataset_version, timestamp
- metrics (aggregate)
- question_results (per-question detail)
- total_latency_ms, total_tokens, estimated_cost
- errors, interpretation, limitations

## Version Pinning
requirements.txt pins exact versions for reproducibility.

## Random Seeds
```python
import numpy as np
np.random.seed(42)
```
Note: LLM outputs are inherently non-deterministic even at temperature=0.
