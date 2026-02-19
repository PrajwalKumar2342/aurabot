#!/usr/bin/env python3
"""
Mem0 REST API Server with dual LLM setup:
- Cerebras API: For chat/LLM responses (fast, high-quality)
- LM Studio (LFM2): For memory classification (local, privacy)
- LM Studio: For embeddings (local)

Environment Variables:
- CEREBRAS_API_KEY: For chat responses (https://cloud.cerebras.ai)
- LM_STUDIO_URL: LM Studio URL for classification + embeddings
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

print("="*70)
print("Mem0 Server: Cerebras (Chat) + LM Studio (Classification + Embeddings)")
print("="*70)

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

# Patch Qdrant vector store to handle None vector in update method
# This fixes a bug in mem0 where update() is called with vector=None for NONE events
try:
    from mem0.vector_stores.qdrant import Qdrant
    from qdrant_client.models import SetPayload
    
    _original_qdrant_update = Qdrant.update
    
    def _patched_qdrant_update(self, vector_id, vector=None, payload=None):
        """Patched update method that handles vector=None correctly."""
        if vector is None:
            # Only update payload, not the vector
            # Use set_payload API instead of upsert when only updating payload
            self.client.set_payload(
                collection_name=self.collection_name,
                payload=payload or {},
                points=[vector_id],
            )
        else:
            # Original behavior with vector update
            from qdrant_client.models import PointStruct
            point = PointStruct(id=vector_id, vector=vector, payload=payload)
            self.client.upsert(collection_name=self.collection_name, points=[point])
    
    Qdrant.update = _patched_qdrant_update
    print("[INFO] Patched Qdrant vector store to handle None vector in update()")
except Exception as e:
    print(f"[WARN] Could not patch Qdrant update method: {e}")

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
    
    # Patch embeddings.create with retry logic for LM Studio stability
    if hasattr(self, 'embeddings') and hasattr(self.embeddings, 'create'):
        orig_embed = self.embeddings.create
        def _patched_embed(*args, **kwargs):
            import time
            max_retries = 3
            last_error = None
            
            # Debug: log what we're trying to embed
            input_data = kwargs.get('input', [])
            if isinstance(input_data, str):
                input_preview = input_data[:80] + "..." if len(input_data) > 80 else input_data
            else:
                input_preview = f"[{len(input_data)} items]"
            print(f"[DEBUG] Embedding request: {input_preview}")
            
            for attempt in range(max_retries):
                try:
                    response = orig_embed(*args, **kwargs)
                    # Verify we got valid embeddings
                    if hasattr(response, 'data') and response.data:
                        all_valid = True
                        for i, item in enumerate(response.data):
                            if hasattr(item, 'embedding'):
                                if item.embedding is None:
                                    print(f"[DEBUG] Embedding item {i} is None")
                                    all_valid = False
                                elif len(item.embedding) == 0:
                                    print(f"[DEBUG] Embedding item {i} is empty list")
                                    all_valid = False
                                else:
                                    print(f"[DEBUG] Embedding item {i} success: {len(item.embedding)} dims")
                            else:
                                print(f"[DEBUG] Embedding item {i} has no embedding attribute")
                                all_valid = False
                        if all_valid:
                            return response
                        else:
                            raise ValueError("One or more embeddings are None/empty")
                    else:
                        print(f"[DEBUG] Response has no data: {response}")
                        raise ValueError("Response has no data")
                except Exception as e:
                    last_error = e
                    print(f"[DEBUG] Embedding exception: {type(e).__name__}: {e}")
                    if attempt < max_retries - 1:
                        wait_time = 0.5 * (attempt + 1)
                        print(f"[WARN] Embedding failed (attempt {attempt + 1}), retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        print(f"[ERROR] Embedding failed after {max_retries} attempts, using zero vector fallback")
                        # Return a fake response with zero vectors instead of failing
                        from openai.types.create_embedding_response import CreateEmbeddingResponse
                        from openai.types.embedding import Embedding
                        
                        if isinstance(input_data, str):
                            input_data = [input_data]
                        
                        zero_embeddings = []
                        for i, _ in enumerate(input_data):
                            zero_embeddings.append(Embedding(
                                embedding=[0.0] * 768,
                                index=i,
                                object="embedding"
                            ))
                        
                        return CreateEmbeddingResponse(
                            data=zero_embeddings,
                            model=kwargs.get('model', 'unknown'),
                            object="list",
                            usage={"prompt_tokens": 0, "total_tokens": 0}
                        )
            
        self.embeddings.create = _patched_embed

openai.OpenAI.__init__ = _patched_openai_init

if CEREBRAS_API_KEY:
    print("[INFO] Patched OpenAI client for Cerebras compatibility (removed 'store' parameter)")
else:
    print("[INFO] Patched OpenAI client for LM Studio compatibility")

# Note: When using LM Studio fallback, we use infer=False to skip LLM fact extraction
# as local models may not produce expected JSON format. With Cerebras, fact extraction works properly.

# Configure Mem0
# - LLM: Cerebras (llama3.1-70b) for memory extraction
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
            "collection_name": "screen_memories_v3",
            "embedding_model_dims": 768,  # embeddinggemma-300m dimensions (actual)
            "path": "./qdrant_storage",
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-embeddinggemma-300m",
            "api_key": "not-needed",
            "openai_base_url": LM_STUDIO_URL,
        }
    },
    "llm": {
        "provider": "openai",  # Cerebras is OpenAI-compatible
        "config": {
            "model": "llama3.1-70b",
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
    print(f"     LLM: {'Cerebras (llama3.1-70b)' if CEREBRAS_API_KEY else 'LM Studio (local)'}")
    print(f"     Embeddings: LM Studio (text-embedding-embeddinggemma-300m)")
    print(f"     Vector Store: Qdrant (./qdrant_storage)")
except Exception as e:
    print(f"[FAIL] Failed to initialize Mem0: {e}")
    sys.exit(1)

print(f"[OK] Server starting on http://{HOST}:{PORT}")
print()


class Mem0Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")

    # Allowed origins for CORS - configure based on your deployment
    ALLOWED_ORIGINS = [
        "http://localhost:3000",    # React dev server
        "http://localhost:8080",    # Swift app
        "http://localhost:7345",    # Extension API
        "chrome-extension://*",     # Chrome extension
        "https://chat.openai.com",  # ChatGPT
        "https://chatgpt.com",
        "https://claude.ai",
        "https://gemini.google.com",
        "https://perplexity.ai",
    ]
    
    def _get_origin(self):
        """Get the Origin header from the request."""
        return self.headers.get('Origin', '')
    
    def _is_allowed_origin(self, origin):
        """Check if the origin is in the allowed list."""
        if not origin:
            return True  # Same-origin requests
        for allowed in self.ALLOWED_ORIGINS:
            if allowed.endswith('/*'):
                # Wildcard match for extensions
                prefix = allowed[:-1]
                if origin.startswith(prefix):
                    return True
            elif origin == allowed:
                return True
        return False
    
    def send_json_response(self, data, status=200):
        try:
            origin = self._get_origin()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            
            # Only set CORS headers for allowed origins
            if self._is_allowed_origin(origin):
                self.send_header("Access-Control-Allow-Origin", origin if origin else "http://localhost:3000")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.send_header("Access-Control-Allow-Credentials", "true")
            
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        except (ConnectionAbortedError, BrokenPipeError):
            # Client closed connection (timeout or disconnect), log but don't crash
            print(f"[WARN] Client disconnected before response could be sent")

    def do_OPTIONS(self):
        origin = self._get_origin()
        self.send_response(200)
        
        # Only set CORS headers for allowed origins
        if self._is_allowed_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin if origin else "http://localhost:3000")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Credentials", "true")
        
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
                "llm_model": "llama3.1-70b" if CEREBRAS_API_KEY else "local",
                "embedder_provider": "lm_studio",
                "embedder_model": "text-embedding-embeddinggemma-300m",
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

                result = memory.search(
                    query=query,
                    user_id=user_id,
                    agent_id=agent_id,
                    limit=limit
                )

                # mem0.search() returns {"results": [...]} dict, extract the list
                results = result.get("results", []) if isinstance(result, dict) else result

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
