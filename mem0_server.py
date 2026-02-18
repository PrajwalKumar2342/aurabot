#!/usr/bin/env python3
"""
Mem0 REST API Server using LM Studio for local embeddings and LLM.
Compatible with screen-memory-assistant Go application.
"""

import os
import sys
import json
import uuid
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Configuration
HOST = os.getenv("MEM0_HOST", "localhost")
PORT = int(os.getenv("MEM0_PORT", "8000"))
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")

print("="*60)
print("Mem0 REST API Server (LM Studio Edition)")
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

# Monkey-patch OpenAI LLM to fix response_format compatibility with LM Studio
_original_generate_response = OpenAILLM.generate_response

def _patched_generate_response(self, messages, response_format=None, **kwargs):
    # Remove response_format as LM Studio doesn't support "json_object" type
    # It only accepts "json_schema" or "text"
    return _original_generate_response(self, messages, **kwargs)

OpenAILLM.generate_response = _patched_generate_response

# Also patch the OpenAI client creation to handle response_format
import openai
_original_openai_init = openai.OpenAI.__init__

def _patched_openai_init(self, *args, **kwargs):
    _original_openai_init(self, *args, **kwargs)
    # Store reference to original method on the instance
    if hasattr(self, 'chat') and hasattr(self.chat, 'completions'):
        orig_create = self.chat.completions.create
        def _patched_create(*args, **kwargs):
            kwargs.pop('response_format', None)
            return orig_create(*args, **kwargs)
        self.chat.completions.create = _patched_create

openai.OpenAI.__init__ = _patched_openai_init
print("[INFO] Patched OpenAI LLM for LM Studio compatibility")

# Note: We use infer=False when calling memory.add() to skip LLM fact extraction
# This avoids issues with lfm2-vl-450m not producing expected JSON format
# The Go app handles vision/LLM analysis; mem0 just stores embeddings for search

# Configure Mem0 to use LM Studio for embeddings
# Note: The Go app handles vision/LLM analysis. Mem0 only needs embeddings for storage.
print()
print("Configuring Mem0 for embedding storage...")

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
            "model": "text-embedding-nomic-embed-text-v1.5",
            "api_key": "not-needed",
            "openai_base_url": LM_STUDIO_URL,
        }
    },
    "llm": {
        "provider": "openai",  # Use openai provider for LM Studio compatibility
        "config": {
            "model": "lfm2-vl-450m",
            "api_key": "not-needed",
            "openai_base_url": LM_STUDIO_URL,
            "temperature": 0.1,
            "max_tokens": 256,
        }
    },
    # Disable custom fact extraction prompts that may cause JSON parsing issues with LM Studio
    "custom_prompt": {
        "facts": None  # Use default/simple fact extraction
    }
}

# Override with OpenAI if key is available (optional)
if os.getenv("OPENAI_API_KEY"):
    print("OPENAI_API_KEY found - will use OpenAI for better performance")
    config = {}  # Use defaults

# Initialize Mem0
try:
    if config:
        memory = Memory.from_config(config_dict=config)
    else:
        memory = Memory()
    print("[OK] Mem0 initialized successfully")
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
                "lm_studio": LM_STUDIO_URL
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

                # Add memory with infer=False to skip LLM fact extraction
                # lfm2-vl-450m doesn't produce expected format for fact extraction
                # The Go app already handles vision/LLM analysis, we just store embeddings
                result = memory.add(
                    messages=messages,
                    user_id=user_id,
                    agent_id=agent_id,
                    metadata=metadata,
                    infer=False  # Skip LLM fact extraction, store raw content
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
                    search_results.append({
                        "memory": {
                            "id": r.get("id", str(uuid.uuid4())),
                            "content": r.get("memory", ""),
                            "user_id": user_id,
                            "metadata": r.get("metadata", {}),
                            "created_at": r.get("created_at", datetime.now().isoformat())
                        },
                        "score": r.get("score", 0.0),
                        "distance": r.get("distance", 0.0)
                    })

                self.send_json_response(search_results)
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
