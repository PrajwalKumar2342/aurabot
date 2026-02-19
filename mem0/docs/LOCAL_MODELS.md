# Local Models Setup

This guide explains how to run **LFM-2-Vision-450M** and **Nomic-Embed-Text-v1.5** locally without any external API dependencies.

## Overview

| Model | Type | Size | Purpose |
|-------|------|------|---------|
| `LiquidAI/LFM-2-Vision-450M` | Vision-Language | ~450M | Chat, vision understanding, Q&A |
| `nomic-ai/nomic-embed-text-v1.5` | Embedding | ~550M | Text embeddings for search/memory |

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or let the scripts auto-install on first run.

### 2. Download Models (One-time)

Download both models:
```bash
python download_models.py
```

Or download individually:
```bash
python download_models.py embedding   # Nomic embed model only
python download_models.py vision      # LFM vision model only
```

Check download status:
```bash
python download_models.py --list
```

Models are saved to `./models/` directory:
- `./models/nomic-embed-text-v1.5/` - Embedding model
- `./models/lfm-2-vision-450m/` - Vision-language model

### 3. Run the Server

**Option A: Standalone Model Server** (Simple, API-only)
```bash
python local_model_server.py
```

**Option B: Mem0 + Local Models** (Full memory system)
```bash
python mem0_local.py
```

## API Endpoints

Once the server is running, the following endpoints are available:

### Health Check
```bash
curl http://localhost:8000/health
```

### List Models
```bash
curl http://localhost:8000/v1/models
```

### Generate Embeddings
```bash
curl -X POST http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Hello, world!",
    "model": "nomic-embed-text-v1.5"
  }'
```

### Chat Completions
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "lfm-2-vision-450m",
    "messages": [
      {"role": "user", "content": "What is machine learning?"}
    ]
  }'
```

### Memory Operations (Mem0 server only)

**Add memory:**
```bash
curl -X POST http://localhost:8000/v1/memories/ \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "I love programming in Python"}],
    "user_id": "user123"
  }'
```

**Search memories:**
```bash
curl -X POST http://localhost:8000/v1/memories/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "programming languages",
    "user_id": "user123"
  }'
```

**Get all memories:**
```bash
curl "http://localhost:8000/v1/memories/?user_id=user123"
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MEM0_HOST` | `localhost` | Server bind address |
| `MEM0_PORT` | `8000` | Server port |
| `MODELS_DIR` | `./models` | Directory for downloaded models |

Example:
```bash
set MEM0_PORT=8080
python mem0_local.py
```

## Scripts Reference

### `download_models.py`
Downloads models from Hugging Face Hub.

```bash
python download_models.py [model_name]

# Options:
python download_models.py all        # Download all models (default)
python download_models.py embedding  # Download Nomic embed model
python download_models.py vision     # Download LFM vision model
python download_models.py --list     # Show download status
python download_models.py --help     # Show help
```

### `local_model_server.py`
Standalone server providing OpenAI-compatible API for local models.
- Auto-downloads models on first run
- Provides embeddings and chat endpoints
- No external dependencies after download

### `mem0_local.py`
Full Mem0 memory server with local models.
- Requires `mem0ai` package
- Provides memory storage, search, and retrieval
- Uses Qdrant for vector storage

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 16 GB |
| Disk | 3 GB free | 5 GB free |
| GPU | Optional | CUDA-compatible GPU |

**Note:** The models will use GPU acceleration automatically if CUDA is available.

## Troubleshooting

### ImportError: No module named 'transformers'
```bash
pip install transformers torch pillow numpy
```

### Model download fails
1. Check internet connection
2. Ensure you have enough disk space (~3GB)
3. Try manual download:
   ```bash
   python -c "from huggingface_hub import snapshot_download; snapshot_download('nomic-ai/nomic-embed-text-v1.5', local_dir='./models/nomic-embed-text-v1.5')"
   ```

### Out of memory
- Close other applications
- Use CPU instead of GPU by setting: `CUDA_VISIBLE_DEVICES=""`
- Reduce batch size in the code

### Slow inference
- Ensure CUDA is available: `python -c "import torch; print(torch.cuda.is_available())"`
- Use GPU for faster inference
- Models are optimized for inference but still require significant compute

## Model Information

### LFM-2-Vision-450M
- **Provider**: Liquid AI
- **Architecture**: Vision-Language Model
- **Parameters**: 450M
- **Context**: 4096 tokens
- **Use cases**: Image understanding, visual Q&A, chat with images

### Nomic-Embed-Text-v1.5
- **Provider**: Nomic AI
- **Type**: Text Embedding Model
- **Dimensions**: 768
- **Max Length**: 2048 tokens
- **Use cases**: Semantic search, text similarity, clustering

## Integration with Existing Code

The local server is OpenAI-compatible, so you can use it with existing clients:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="local"  # Not used but required
)

# Embeddings
response = client.embeddings.create(
    model="nomic-embed-text-v1.5",
    input="Hello, world!"
)

# Chat
response = client.chat.completions.create(
    model="lfm-2-vision-450m",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## License

These scripts are provided as-is. Please check the model licenses on Hugging Face:
- [LFM-2-Vision-450M](https://huggingface.co/LiquidAI/LFM-2-Vision-450M)
- [Nomic-Embed-Text-v1.5](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5)
