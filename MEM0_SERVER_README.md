# Mem0 Server for Screen Memory Assistant

This project requires a Mem0 REST API server running at `http://localhost:8000`.

## Quick Start

### 1. Start LM Studio

1. Open **LM Studio**
2. **Load an embedding model** (required for Mem0):
   - Search for "nomic-embed-text" or "text-embedding"
   - Load it (this creates the memory embeddings)
3. **Start the local server**:
   - Click "Start Server" button (right sidebar)
   - Default URL: `http://localhost:1234`

**Note:** The vision/chat model for analyzing screenshots is handled separately by your Go app via LM Studio. The Mem0 server only needs the embedding model.

### 2. Start Mem0 Server

```bash
# Using batch file (Windows)
start_mem0_server.bat

# Or directly
python mem0_server.py
```

### 3. Run Your Go Application

```bash
go run .
# or
make run
```

---

## How It Works

| Component | Purpose | Endpoint |
|-----------|---------|----------|
| LM Studio | Provides embeddings + LLM | `http://localhost:1234/v1` |
| mem0_server.py | REST API wrapper for Mem0 | `http://localhost:8000` |
| Go App | Screen capture + memory | Uses `http://localhost:8000` |

---

## Troubleshooting

### "Cannot connect to LM Studio"
- Make sure LM Studio is running
- Click "Start Server" in LM Studio
- Check that the port is 1234 (or update `LM_STUDIO_URL` env var)

### "Failed to initialize Mem0"
- Ensure you have an **embedding model** loaded in LM Studio
- Check LM Studio logs for errors

### "No module named 'mem0'"
```bash
pip install mem0ai
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LM_STUDIO_URL` | `http://localhost:1234/v1` | LM Studio API endpoint |
| `MEM0_HOST` | `localhost` | Mem0 server bind host |
| `MEM0_PORT` | `8000` | Mem0 server bind port |
| `OPENAI_API_KEY` | - | Optional: Use OpenAI instead of LM Studio |

---

## API Endpoints

Once running, these endpoints are available:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/v1/memories/` | POST | Add a new memory |
| `/v1/memories/` | GET | Get all memories |
| `/v1/memories/search/` | POST | Search memories |

---

## Storage

Mem0 stores data locally:
- **Vector DB**: `./qdrant_storage/` (Qdrant)
- **Metadata**: `~/.mem0/history.db` (SQLite)

Data persists between restarts.
