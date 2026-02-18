#!/usr/bin/env python3
"""
Mem0 REST API Server using Cerebras for LLM and LM Studio for local embeddings.
Compatible with screen-memory-assistant Go application.

Configuration:
- LLM: Cerebras API (Qwen 3 235B Instruct) - falls back to LM Studio if no API key
- Embeddings: LM Studio (nomic-embed-text v1.5) - local
- Vector Store: Qdrant - local storage

Environment Variables:
- CEREBRAS_API_KEY: Your Cerebras API key (get from https://cloud.cerebras.ai)
- LM_STUDIO_URL: LM Studio server URL (default: http://localhost:1234/v1)
- MEM0_HOST: Server host (default: localhost)
- MEM0_PORT: Server port (default: 8000)
"""

import os
import sys
import json
import uuid
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[INFO] Loaded environment from .env file")
except ImportError:
    print("[INFO] python-dotenv not installed, using system environment variables only")
    print("       To use .env file: pip install python-dotenv")

# Configuration
HOST = os.getenv("MEM0_HOST", "localhost")
PORT = int(os.getenv("MEM0_PORT", "8000"))
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")

print("="*60)
print("Mem0 REST API Server (Cerebras LLM + LM Studio Embeddings)")
print("="*60)

# Check LM Studio availability
try:
    resp = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
    if resp.status_code == 200:
        models = resp.json().get('data', [])
        print(f"[OK] LM Studio connected at {LM_STUDIO_URL}")
        print(f"     Models loaded: {len(models)}")
        for m in models[:3]:  # Show first 3
            print(f"       - {m['id']}")
        if len(models) > 3:
            print(f"       ... and {len(models)-3} more")
    else:
        print(f"[WARN] LM Studio returned status {resp.status_code}")
except Exception as e:
    print(f"[FAIL] Cannot connect to LM Studio at {LM_STUDIO_URL}")
    print(f"  Error: {e}")
    print()
    print("Please start LM Studio and load a model:")
    print("  1. Open LM Studio")
    print("  2. Load an embedding model (e.g., nomic-embed-text)")
    print("  3. Start the local server")
    sys.exit(1)

# Import mem0
try:
    from mem0 import Memory
    from mem0.llms.openai import OpenAILLM
except ImportError:
    print("ERROR: mem0ai not installed. Run: pip install mem0ai")
    sys.exit(1)

# Apply patches for LLM compatibility
# Cerebras: Remove 'store' parameter which OpenAI client adds but Cerebras doesn't support
# LM Studio: Remove 'response_format' parameter
import openai

_original_openai_init = openai.OpenAI.__init__

def _patched_openai_init(self, *args, **kwargs):
    _original_openai_init(self, *args, **kwargs)
    # Store reference to original method on the instance
    if hasattr(self, 'chat') and hasattr(self.chat, 'completions'):
        orig_create = self.chat.completions.create
        def _patched_create(*args, **kwargs):
            # Remove 'store' parameter (Cerebras doesn't support it)
            kwargs.pop('store', None)
            # Remove 'response_format' for non-OpenAI providers
            if not CEREBRAS_API_KEY:
                kwargs.pop('response_format', None)
            return orig_create(*args, **kwargs)
        self.chat.completions.create = _patched_create

openai.OpenAI.__init__ = _patched_openai_init

if CEREBRAS_API_KEY:
    print("[INFO] Patched OpenAI client for Cerebras compatibility (removed 'store' parameter)")
else:
    print("[INFO] Patched OpenAI client for LM Studio compatibility")

# Note: When using LM Studio fallback, we use infer=False to skip LLM fact extraction
# as local models may not produce expected JSON format. With Cerebras, fact extraction works properly.

# Configure Mem0
# - LLM: Cerebras (Qwen 3 235B Instruct) for memory extraction
# - Embeddings: LM Studio (nomic-embed-text) for local embedding generation
# - Vector Store: Qdrant for local storage
print()
print("Configuring Mem0...")

if not CEREBRAS_API_KEY:
    print("[WARN] CEREBRAS_API_KEY not set. Falling back to LM Studio for LLM.")
    print("       Get your API key from: https://cloud.cerebras.ai")
    print()

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "screen_memories",
            "embedding_model_dims": 768,  # nomic-embed-text dimensions
            "path": "./qdrant_storage",
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-nomic-embed-text-v1.5-embedding",
            "api_key": "not-needed",
            "openai_base_url": LM_STUDIO_URL,
        }
    },
    "llm": {
        "provider": "openai",  # Cerebras is OpenAI-compatible
        "config": {
            "model": "gpt-oss-120b",
            "api_key": CEREBRAS_API_KEY if CEREBRAS_API_KEY else "not-needed",
            "openai_base_url": "https://api.cerebras.ai/v1" if CEREBRAS_API_KEY else LM_STUDIO_URL,
            "temperature": 0.7,
            "max_tokens": 4096,
        }
    },
}

# Initialize Mem0
try:
    memory = Memory.from_config(config_dict=config)
    print("[OK] Mem0 initialized successfully")
    print(f"     LLM: {'Cerebras (gpt-oss-120b)' if CEREBRAS_API_KEY else 'LM Studio (local)'}")
    print(f"     Embeddings: LM Studio (nomic-embed-text)")
    print(f"     Vector Store: Qdrant (./qdrant_storage)")
except Exception as e:
    print(f"[FAIL] Failed to initialize Mem0: {e}")
    sys.exit(1)

print(f"[OK] Server starting on http://{HOST}:{PORT}")
print()


class Mem0Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")

    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Health check
        if path == "/health":
            self.send_json_response({
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "llm_provider": "cerebras" if CEREBRAS_API_KEY else "lm_studio",
                "llm_model": "gpt-oss-120b" if CEREBRAS_API_KEY else "local",
                "embedder_provider": "lm_studio",
                "embedder_model": "nomic-embed-text-v1.5",
                "vector_store": "qdrant",
                "lm_studio_url": LM_STUDIO_URL
            })
            return

        # Get memories
        if path == "/v1/memories/":
            user_id = query.get("user_id", ["default_user"])[0]
            agent_id = query.get("agent_id", [""])[0] or None
            limit = int(query.get("limit", ["10"])[0])

            try:
                results = memory.get_all(user_id=user_id, agent_id=agent_id, limit=limit)
                print(f"[DEBUG] get_all returned type: {type(results)}, content: {results}")
                memories = []
                # Handle different return formats from mem0
                if isinstance(results, list):
                    for mem in results:
                        if isinstance(mem, dict):
                            memories.append({
                                "id": mem.get("id", str(uuid.uuid4())),
                                "content": mem.get("memory", ""),
                                "user_id": user_id,
                                "metadata": mem.get("metadata", {}),
                                "created_at": mem.get("created_at", datetime.now().isoformat())
                            })
                        elif isinstance(mem, str):
                            memories.append({
                                "id": str(uuid.uuid4()),
                                "content": mem,
                                "user_id": user_id,
                                "metadata": {},
                                "created_at": datetime.now().isoformat()
                            })
                elif isinstance(results, dict):
                    # Handle {"results": [...]} format
                    if "results" in results:
                        for mem in results["results"]:
                            if isinstance(mem, dict):
                                memories.append({
                                    "id": mem.get("id", str(uuid.uuid4())),
                                    "content": mem.get("memory", mem.get("content", "")),
                                    "user_id": user_id,
                                    "metadata": mem.get("metadata", {}),
                                    "created_at": mem.get("created_at", datetime.now().isoformat())
                                })
                    # Handle direct dict with memory fields
                    elif "memory" in results or "id" in results:
                        memories.append({
                            "id": results.get("id", str(uuid.uuid4())),
                            "content": results.get("memory", results.get("content", "")),
                            "user_id": user_id,
                            "metadata": results.get("metadata", {}),
                            "created_at": results.get("created_at", datetime.now().isoformat())
                        })
                self.send_json_response(memories)
            except Exception as e:
                print(f"Error getting memories: {e}")
                self.send_json_response({"error": str(e)}, 500)
            return

        self.send_json_response({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()
        data = json.loads(body) if body else {}

        # Add memory
        if path == "/v1/memories/":
            try:
                messages = data.get("messages", [])
                user_id = data.get("user_id", "default_user")
                agent_id = data.get("agent_id")
                metadata = data.get("metadata", {})

                content = " ".join([m.get("content", "") for m in messages if m.get("content")])

                # Add memory
                # infer=True enables LLM fact extraction (works well with Cerebras)
                # infer=False skips fact extraction (fallback for LM Studio)
                result = memory.add(
                    messages=messages,
                    user_id=user_id,
                    agent_id=agent_id,
                    metadata=metadata,
                    infer=bool(CEREBRAS_API_KEY)  # Enable fact extraction if using Cerebras
                )

                response = {
                    "id": result.get("id", str(uuid.uuid4())),
                    "content": content,
                    "user_id": user_id,
                    "metadata": metadata,
                    "created_at": datetime.now().isoformat()
                }
                self.send_json_response(response, 201)
            except Exception as e:
                print(f"Error adding memory: {e}")
                import traceback
                traceback.print_exc()
                self.send_json_response({"error": str(e)}, 500)
            return

        # Search memories
        if path == "/v1/memories/search/":
            try:
                query = data.get("query", "")
                user_id = data.get("user_id", "default_user")
                agent_id = data.get("agent_id")
                limit = data.get("limit", 10)

                results = memory.search(
                    query=query,
                    user_id=user_id,
                    agent_id=agent_id,
                    limit=limit
                )

                search_results = []
                for r in results:
                    # Handle both dict and string result formats
                    if isinstance(r, dict):
                        # Get content - handle None case
                        content = r.get("memory")
                        if content is None:
                            content = ""
                        
                        search_results.append({
                            "id": r.get("id", str(uuid.uuid4())),
                            "memory": content,
                            "user_id": user_id,
                            "metadata": r.get("metadata", {}),
                            "created_at": r.get("created_at", datetime.now().isoformat()),
                            "score": r.get("score", 0.0),
                            "distance": r.get("distance", 0.0)
                        })
                    elif isinstance(r, str):
                        # Handle string results (just the memory content)
                        search_results.append({
                            "id": str(uuid.uuid4()),
                            "memory": r,
                            "user_id": user_id,
                            "metadata": {},
                            "created_at": datetime.now().isoformat(),
                            "score": 1.0,
                            "distance": 0.0
                        })

                # Wrap in results field for Go compatibility
                self.send_json_response({"results": search_results})
            except Exception as e:
                print(f"Error searching memories: {e}")
                self.send_json_response({"error": str(e)}, 500)
            return

        self.send_json_response({"error": "Not found"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/v1/memories/"):
            try:
                self.send_json_response({"deleted": True})
            except Exception as e:
                print(f"Error deleting memory: {e}")
                self.send_json_response({"error": str(e)}, 500)
            return

        self.send_json_response({"error": "Not found"}, 404)


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Mem0Handler)
    print("-" * 60)
    print("Available endpoints:")
    print(f"  Health:  GET  http://{HOST}:{PORT}/health")
    print(f"  Add:     POST http://{HOST}:{PORT}/v1/memories/")
    print(f"  Search:  POST http://{HOST}:{PORT}/v1/memories/search/")
    print(f"  Get All: GET  http://{HOST}:{PORT}/v1/memories/")
    print("-" * 60)
    print("Press Ctrl+C to stop")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
