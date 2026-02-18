#!/usr/bin/env python3
"""
Supermemory REST API Server using Cerebras for LLM and LM Studio for local embeddings.
Compatible with screen-memory-assistant Go application.

Configuration:
- LLM: Cerebras API (Qwen 3 235B Instruct) - falls back to LM Studio if no API key
- Embeddings: Supermemory handles embeddings internally
- Memory Store: Supermemory.ai cloud service

Environment Variables:
- SUPERMEMORY_API_KEY: Your Supermemory API key (required, get from https://supermemory.ai)
- CEREBRAS_API_KEY: Your Cerebras API key (optional, get from https://cloud.cerebras.ai)
- LM_STUDIO_URL: LM Studio server URL (default: http://localhost:1234/v1)
- SUPERMEMORY_HOST: Server host (default: localhost)
- SUPERMEMORY_PORT: Server port (default: 8000)
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
HOST = os.getenv("SUPERMEMORY_HOST", "localhost")
PORT = int(os.getenv("SUPERMEMORY_PORT", "8000"))
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
SUPERMEMORY_API_KEY = os.getenv("SUPERMEMORY_API_KEY", "")

print("="*60)
print("Supermemory REST API Server")
print("="*60)

# Check Supermemory API key
if not SUPERMEMORY_API_KEY:
    print("[ERROR] SUPERMEMORY_API_KEY not set!")
    print("        Get your API key from: https://supermemory.ai")
    print("        Set it as environment variable or in .env file")
    sys.exit(1)

# Import supermemory
try:
    from supermemory import Supermemory
except ImportError:
    print("ERROR: supermemory not installed. Run: pip install supermemory")
    sys.exit(1)

# Initialize Supermemory client
print()
print("Configuring Supermemory...")

try:
    sm_client = Supermemory(api_key=SUPERMEMORY_API_KEY)
    print("[OK] Supermemory client initialized")
except Exception as e:
    print(f"[FAIL] Failed to initialize Supermemory: {e}")
    sys.exit(1)

# Check LM Studio availability (for LLM features)
llm_available = False
if CEREBRAS_API_KEY:
    print("[INFO] Using Cerebras for LLM")
    llm_available = True
else:
    try:
        resp = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get('data', [])
            print(f"[OK] LM Studio connected at {LM_STUDIO_URL}")
            print(f"     Models loaded: {len(models)}")
            llm_available = True
        else:
            print(f"[WARN] LM Studio returned status {resp.status_code}")
    except Exception as e:
        print(f"[WARN] Cannot connect to LM Studio at {LM_STUDIO_URL}")
        print(f"       Error: {e}")
        print("       LLM features will be disabled")

print(f"[OK] Server starting on http://{HOST}:{PORT}")
print()


class SupermemoryHandler(BaseHTTPRequestHandler):
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
                "llm_provider": "cerebras" if CEREBRAS_API_KEY else ("lm_studio" if llm_available else "none"),
                "llm_model": "gpt-oss-120b" if CEREBRAS_API_KEY else "local",
                "memory_provider": "supermemory",
                "lm_studio_url": LM_STUDIO_URL
            })
            return

        # Get memories
        if path == "/v1/memories/":
            container_tag = query.get("agent_id", ["screen_memories"])[0]
            limit = int(query.get("limit", ["10"])[0])

            try:
                # Supermemory requires a non-empty query, so we search for a space
                # which will match almost everything
                results = sm_client.search.execute(
                    q="*",
                    container_tags=[container_tag],
                    limit=limit
                )

                memories = []
                for result in results.results:
                    # Convert Pydantic model to dict if needed
                    if hasattr(result, 'model_dump'):
                        # Pydantic v2
                        result_dict = result.model_dump()
                    elif hasattr(result, 'dict'):
                        # Pydantic v1
                        result_dict = result.dict()
                    else:
                        result_dict = result
                    
                    # Get content - handle None case
                    content = result_dict.get("content")
                    if content is None:
                        content = ""
                    
                    memories.append({
                        "id": result_dict.get("document_id") or result_dict.get("id") or str(uuid.uuid4()),
                        "content": content,
                        "user_id": container_tag,
                        "metadata": result_dict.get("metadata") or {},
                        "created_at": result_dict.get("created_at") or result_dict.get("createdAt") or datetime.now().isoformat()
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
                agent_id = data.get("agent_id", "screen_memories")
                metadata = data.get("metadata", {})

                # Extract content from messages
                content = " ".join([m.get("content", "") for m in messages if m.get("content")])
                if not content:
                    content = data.get("content", "")

                # Add memory to Supermemory
                result = sm_client.add(
                    content=content,
                    container_tags=[agent_id],
                    metadata=metadata
                )

                response = {
                    "id": getattr(result, 'id', str(uuid.uuid4())),
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
                query = data.get("query", data.get("q", ""))
                user_id = data.get("user_id", "default_user")
                agent_id = data.get("agent_id", "screen_memories")
                limit = data.get("limit", 10)

                results = sm_client.search.execute(
                    q=query,
                    container_tags=[agent_id],
                    limit=limit
                )

                search_results = []
                for result in results.results:
                    # Convert Pydantic model to dict if needed
                    if hasattr(result, 'model_dump'):
                        # Pydantic v2
                        result_dict = result.model_dump()
                    elif hasattr(result, 'dict'):
                        # Pydantic v1
                        result_dict = result.dict()
                    else:
                        result_dict = result
                    
                    # Get content - handle None case (Supermemory returns null sometimes)
                    content = result_dict.get("content")
                    summary = result_dict.get("summary")
                    title = result_dict.get("title")
                    
                    print(f"[DEBUG] content={content!r}, summary={summary!r}, title={title!r}")
                    
                    # Use first non-empty field
                    final_content = content or summary or title or ""
                    
                    search_results.append({
                        "id": result_dict.get("document_id") or result_dict.get("id") or str(uuid.uuid4()),
                        "memory": final_content,
                        "user_id": user_id,
                        "metadata": result_dict.get("metadata") or {},
                        "created_at": datetime.now().isoformat(),
                        "score": result_dict.get("score") or 0.0,
                        "distance": result_dict.get("distance") or 0.0
                    })

                # Wrap in results field for Go compatibility
                self.send_json_response({"results": search_results})
            except Exception as e:
                print(f"Error searching memories: {e}")
                import traceback
                traceback.print_exc()
                self.send_json_response({"error": str(e)}, 500)
            return

        self.send_json_response({"error": "Not found"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/v1/memories/"):
            try:
                memory_id = path.split("/")[-1]
                if memory_id and memory_id != "memories":
                    # Delete from Supermemory
                    sm_client.delete(id=memory_id)
                self.send_json_response({"deleted": True})
            except Exception as e:
                print(f"Error deleting memory: {e}")
                self.send_json_response({"error": str(e)}, 500)
            return

        self.send_json_response({"error": "Not found"}, 404)


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), SupermemoryHandler)
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
