#!/usr/bin/env python3
"""
Supermemory Local Server - Uses local models for vision and embeddings.
This is a standalone server that doesn't require LM Studio.

Requires:
- pip install supermemory transformers Pillow torch
- Models downloaded via download_models.py

Environment Variables:
- SUPERMEMORY_API_KEY: Your Supermemory API key (required)
- SUPERMEMORY_HOST: Server host (default: localhost)
- SUPERMEMORY_PORT: Server port (default: 8000)
"""

import os
import sys
import json
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[INFO] Loaded environment from .env file")
except ImportError:
    pass

# Configuration
HOST = os.getenv("SUPERMEMORY_HOST", "localhost")
PORT = int(os.getenv("SUPERMEMORY_PORT", "8000"))
SUPERMEMORY_API_KEY = os.getenv("SUPERMEMORY_API_KEY", "")

print("="*60)
print("Supermemory Local Server (with Local Models)")
print("="*60)

# Check Supermemory API key
if not SUPERMEMORY_API_KEY:
    print("[ERROR] SUPERMEMORY_API_KEY not set!")
    print("        Get your API key from: https://supermemory.ai")
    sys.exit(1)

# Import supermemory
try:
    from supermemory import Supermemory
except ImportError:
    print("ERROR: supermemory not installed. Run: pip install supermemory")
    sys.exit(1)

# Try to import local model dependencies
try:
    from transformers import AutoModelForVision2Seq, AutoProcessor
    import torch
    from PIL import Image
    import io
    LOCAL_MODELS_AVAILABLE = True
    print("[INFO] Local model dependencies available")
except ImportError as e:
    LOCAL_MODELS_AVAILABLE = False
    print(f"[WARN] Local models not available: {e}")
    print("       Install with: pip install transformers Pillow torch")

# Initialize Supermemory client
print()
print("Configuring Supermemory...")

try:
    sm_client = Supermemory(api_key=SUPERMEMORY_API_KEY)
    print("[OK] Supermemory client initialized")
except Exception as e:
    print(f"[FAIL] Failed to initialize Supermemory: {e}")
    sys.exit(1)

# Initialize local models if available
vision_model = None
vision_processor = None
if LOCAL_MODELS_AVAILABLE:
    print()
    print("Loading local vision model...")
    try:
        model_path = "./models/LFM-2-Vision-450M"
        if os.path.exists(model_path):
            vision_processor = AutoProcessor.from_pretrained(model_path)
            vision_model = AutoModelForVision2Seq.from_pretrained(
                model_path,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            print("[OK] Local vision model loaded")
        else:
            print(f"[WARN] Model not found at {model_path}")
            print("       Run: python download_models.py")
    except Exception as e:
        print(f"[WARN] Failed to load local model: {e}")

print(f"[OK] Server starting on http://{HOST}:{PORT}")
print()


def analyze_image_with_local_model(image_data):
    """Analyze image using local vision model."""
    if vision_model is None or vision_processor is None:
        return {
            "summary": "Screen captured (local model not available)",
            "context": "unknown",
            "activities": [],
            "key_elements": [],
            "user_intent": "unknown"
        }
    
    try:
        # Load image
        image = Image.open(io.BytesIO(image_data))
        
        # Downscale image to 1280x720 for LFM2
        target_size = (1280, 720)
        image = image.resize(target_size, Image.Resampling.LANCZOS)
        
        # Prepare prompt
        prompt = "Describe what you see in this screenshot. What is the user doing?"
        
        # Process
        inputs = vision_processor(images=image, text=prompt, return_tensors="pt")
        
        # Generate with temperature 0.5
        with torch.no_grad():
            outputs = vision_model.generate(
                **inputs,
                max_new_tokens=100,
                do_sample=True,
                temperature=0.5
            )
        
        # Decode
        description = vision_processor.batch_decode(outputs, skip_special_tokens=True)[0]
        
        return {
            "summary": description,
            "context": "screen_capture",
            "activities": ["using_computer"],
            "key_elements": [],
            "user_intent": "working"
        }
    except Exception as e:
        print(f"Error analyzing image: {e}")
        return {
            "summary": "Screen captured (analysis failed)",
            "context": "unknown",
            "activities": [],
            "key_elements": [],
            "user_intent": "unknown"
        }


class SupermemoryLocalHandler(BaseHTTPRequestHandler):
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
                "llm_provider": "local" if LOCAL_MODELS_AVAILABLE else "none",
                "memory_provider": "supermemory",
                "local_models_available": LOCAL_MODELS_AVAILABLE
            })
            return

        # Get memories
        if path == "/v1/memories/":
            container_tag = query.get("agent_id", ["screen_memories"])[0]
            limit = int(query.get("limit", ["10"])[0])

            try:
                # Supermemory requires a non-empty query, use wildcard
                results = sm_client.search.execute(
                    q="*",
                    container_tags=[container_tag],
                    limit=limit
                )

                memories = []
                for result in results.results:
                    # Convert Pydantic model to dict if needed
                    if hasattr(result, 'model_dump'):
                        result_dict = result.model_dump()
                    elif hasattr(result, 'dict'):
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
                        result_dict = result.model_dump()
                    elif hasattr(result, 'dict'):
                        result_dict = result.dict()
                    else:
                        result_dict = result
                    
                    # Get content - handle None case
                    content = result_dict.get("content")
                    if content is None:
                        content = ""
                    
                    search_results.append({
                        "id": result_dict.get("document_id") or result_dict.get("id") or str(uuid.uuid4()),
                        "memory": content,
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

        # Analyze image with local model
        if path == "/v1/analyze":
            try:
                if not LOCAL_MODELS_AVAILABLE:
                    self.send_json_response({"error": "Local models not available"}, 503)
                    return

                # Expect base64 encoded image
                image_b64 = data.get("image", "")
                if not image_b64:
                    self.send_json_response({"error": "No image provided"}, 400)
                    return

                import base64
                image_data = base64.b64decode(image_b64)
                result = analyze_image_with_local_model(image_data)
                self.send_json_response(result)
            except Exception as e:
                print(f"Error analyzing image: {e}")
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
                    sm_client.delete(id=memory_id)
                self.send_json_response({"deleted": True})
            except Exception as e:
                print(f"Error deleting memory: {e}")
                self.send_json_response({"error": str(e)}, 500)
            return

        self.send_json_response({"error": "Not found"}, 404)


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), SupermemoryLocalHandler)
    print("-" * 60)
    print("Available endpoints:")
    print(f"  Health:  GET  http://{HOST}:{PORT}/health")
    print(f"  Add:     POST http://{HOST}:{PORT}/v1/memories/")
    print(f"  Search:  POST http://{HOST}:{PORT}/v1/memories/search/")
    print(f"  Get All: GET  http://{HOST}:{PORT}/v1/memories/")
    print(f"  Analyze: POST http://{HOST}:{PORT}/v1/analyze")
    print("-" * 60)
    print("Press Ctrl+C to stop")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
