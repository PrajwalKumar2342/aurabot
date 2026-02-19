#!/usr/bin/env python3
"""
Mem0 REST API Server using local models (no external dependencies).

This is a modified version of mem0_server.py that uses locally downloaded models
instead of requiring LM Studio or external API services.

Models:
- LLM: LFM-2-Vision-450M (local)
- Embeddings: Google Embedding Gemma 300M FP8 (local, GPU required)
- Vector Store: Qdrant (local storage)

Environment Variables:
- MEM0_HOST: Server host (default: localhost)
- MEM0_PORT: Server port (default: 8000)
- MODELS_DIR: Directory to store downloaded models (default: ./models)

Requirements:
    - GPU is required for embedding model
    - Run `huggingface-cli login` before first use

Usage:
    # First, download the models (one-time)
    python scripts/download_models.py
    
    # Then, start the server
    cd python/src && python mem0_local.py
"""

import os
import sys
import json
import uuid
import time
import io
import base64
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[INFO] Loaded environment from .env file")
except ImportError:
    pass

# Configuration
HOST = os.getenv("MEM0_HOST", "localhost")
PORT = int(os.getenv("MEM0_PORT", "8000"))
MODELS_DIR = Path(os.getenv("MODELS_DIR", "./models"))

print("="*70)
print("Mem0 REST API Server (Local Models - No External Dependencies)")
print("="*70)
print()

# ============================================================================
# Model Loading
# ============================================================================

class LocalModelManager:
    """Manages local model loading and inference."""
    
    def __init__(self):
        self.embedding_model = None
        self.embedding_tokenizer = None
        self.llm_model = None
        self.llm_processor = None
        self.device = "cpu"
        
        # Try CUDA
        try:
            import torch
            if torch.cuda.is_available():
                self.device = "cuda"
                print(f"[OK] Using CUDA for GPU acceleration")
            else:
                print(f"[INFO] Using CPU for inference")
        except ImportError:
            pass
    
    def load_embedding_model(self):
        """Load Google Embedding Gemma model (GPU required)."""
        from transformers import AutoTokenizer, AutoModel
        import torch
        
        model_path = MODELS_DIR / "embeddinggemma-300m-f8"
        
        if not model_path.exists():
            print(f"[ERROR] Embedding model not found at {model_path}")
            print("[INFO] Running automatic setup...")
            
            # Try to auto-setup
            setup_script = Path(__file__).parent.parent.parent.parent / "scripts" / "auto_setup.py"
            if setup_script.exists():
                import subprocess
                result = subprocess.run([sys.executable, str(setup_script)])
                if result.returncode != 0:
                    print("[ERROR] Automatic setup failed. Please run manually:")
                    print(f"       python {setup_script}")
                    sys.exit(1)
                # Re-check after setup
                if not model_path.exists():
                    print("[ERROR] Model still not found after setup.")
                    sys.exit(1)
            else:
                print("[INFO] Please run: python scripts/download_models.py")
                print("[INFO] Note: You must run `huggingface-cli login` first")
                sys.exit(1)
        
        # GPU check for embedding model
        if self.device != "cuda":
            print("[ERROR] GPU is required for embedding model (google/embeddinggemma-300m-f8)")
            print("[INFO] Please ensure CUDA is available or use a different embedding model")
            sys.exit(1)
        
        print(f"[INFO] Loading Google Embedding Gemma 300M FP8 model...")
        
        self.embedding_tokenizer = AutoTokenizer.from_pretrained(
            model_path, trust_remote_code=True, local_files_only=True
        )
        self.embedding_model = AutoModel.from_pretrained(
            model_path, trust_remote_code=True, local_files_only=True,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        self.embedding_model.to(self.device)
        self.embedding_model.eval()
        
        print(f"[OK] Embedding model loaded")
    
    def load_llm_model(self):
        """Load LFM vision model for LLM tasks."""
        from transformers import AutoProcessor, AutoModelForVision2Seq
        
        model_path = MODELS_DIR / "lfm-2-vision-450m"
        
        if not model_path.exists():
            print(f"[ERROR] LLM model not found at {model_path}")
            print("[INFO] Running automatic setup...")
            
            # Try to auto-setup
            setup_script = Path(__file__).parent.parent.parent.parent / "scripts" / "auto_setup.py"
            if setup_script.exists():
                import subprocess
                result = subprocess.run([sys.executable, str(setup_script)])
                if result.returncode != 0:
                    print("[ERROR] Automatic setup failed. Please run manually:")
                    print(f"       python {setup_script}")
                    sys.exit(1)
                # Re-check after setup
                if not model_path.exists():
                    print("[ERROR] Model still not found after setup.")
                    sys.exit(1)
            else:
                print("[INFO] Please run: python scripts/download_models.py")
                sys.exit(1)
        
        print(f"[INFO] Loading LLM model...")
        
        self.llm_processor = AutoProcessor.from_pretrained(
            model_path, trust_remote_code=True, local_files_only=True
        )
        self.llm_model = AutoModelForVision2Seq.from_pretrained(
            model_path, trust_remote_code=True, local_files_only=True
        )
        self.llm_model.to(self.device)
        self.llm_model.eval()
        
        print(f"[OK] LLM model loaded")
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts using Gemma model."""
        import torch
        
        if self.embedding_model is None:
            self.load_embedding_model()
        
        # Gemma doesn't use task prefixes like Nomic
        # Just use raw texts
        
        embeddings = []
        batch_size = 8
        
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                # Gemma supports up to 8192 tokens
                encoded = self.embedding_tokenizer(
                    batch, padding=True, truncation=True,
                    return_tensors="pt", max_length=8192
                )
                encoded = {k: v.to(self.device) for k, v in encoded.items()}
                
                output = self.embedding_model(**encoded)
                
                # Mean pooling (Gemma uses similar pooling strategy)
                mask = encoded["attention_mask"].unsqueeze(-1).float()
                embeddings_batch = (output[0] * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
                embeddings_batch = torch.nn.functional.normalize(embeddings_batch, p=2, dim=1)
                
                embeddings.extend(embeddings_batch.cpu().numpy().tolist())
        
        return embeddings
    
    def chat(self, messages: List[Dict[str, Any]], max_tokens: int = 512) -> str:
        """Generate chat completion."""
        if self.llm_model is None:
            self.load_llm_model()
        
        # Convert messages to simple text prompt
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if isinstance(content, list):
                # Extract text from content items
                texts = [item.get("text", "") for item in content if item.get("type") == "text"]
                content = " ".join(texts)
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append("Assistant:")
        prompt = "\n".join(prompt_parts)
        
        # Generate
        import torch
        inputs = self.llm_processor(text=prompt, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.llm_model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
            )
        
        response = self.llm_processor.decode(outputs[0], skip_special_tokens=True)
        
        # Extract just the assistant's response
        if "Assistant:" in response:
            response = response.split("Assistant:")[-1].strip()
        
        return response


# Initialize model manager
model_manager = LocalModelManager()

# ============================================================================
# Mem0 Integration
# ============================================================================

try:
    from mem0 import Memory
    from mem0.llms.openai import OpenAILLM
    HAS_MEM0 = True
except ImportError:
    print("[WARN] mem0ai not installed. Running in API-only mode.")
    print("       To use Mem0 features: pip install mem0ai")
    HAS_MEM0 = False
    Memory = None

# Custom embedder and LLM classes for Mem0
class LocalEmbedder:
    """Local embedding provider for Mem0."""
    
    def __init__(self):
        pass
    
    def embed(self, text: str, memory_type: str = "text") -> List[float]:
        """Embed a single text."""
        result = model_manager.embed([text])
        return result[0] if result else []


class LocalLLM:
    """Local LLM provider for Mem0."""
    
    def generate(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Generate response from messages."""
        return model_manager.chat(messages, max_tokens=kwargs.get('max_tokens', 512))


# Configure Mem0
memory = None
if HAS_MEM0:
    print()
    print("Configuring Mem0 with local models...")
    
    # Pre-load models
    model_manager.load_embedding_model()
    model_manager.load_llm_model()
    
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "screen_memories",
                "embedding_model_dims": 768,
                "path": "./qdrant_storage",
            }
        },
        "embedder": {
            "provider": "openai",  # We'll override the embedding function
            "config": {
                "model": "nomic-embed-text-v1.5",
                "api_key": "local",
                "openai_base_url": f"http://{HOST}:{PORT}/v1",
            }
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": "lfm-2-vision-450m",
                "api_key": "local",
                "openai_base_url": f"http://{HOST}:{PORT}/v1",
                "temperature": 0.7,
                "max_tokens": 512,
            }
        },
    }
    
    try:
        memory = Memory.from_config(config_dict=config)
        print("[OK] Mem0 initialized successfully")
    except Exception as e:
        print(f"[WARN] Failed to initialize Mem0: {e}")
        print("       Running in API-only mode")

print()

# ============================================================================
# HTTP Server
# ============================================================================

class Mem0LocalHandler(BaseHTTPRequestHandler):
    """HTTP handler for Mem0 with local models."""
    
    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")
    
    def send_json_response(self, data: dict, status: int = 200):
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
                "llm_provider": "local (lfm-2-vision-450m)",
                "embedder_provider": "local (nomic-embed-text-v1.5)",
                "vector_store": "qdrant" if HAS_MEM0 else "disabled",
            })
            return
        
        # List models (OpenAI compatible)
        if path == "/v1/models":
            self.send_json_response({
                "object": "list",
                "data": [
                    {
                        "id": "nomic-embed-text-v1.5",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "local"
                    },
                    {
                        "id": "lfm-2-vision-450m",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "local"
                    }
                ]
            })
            return
        
        # Get memories
        if path == "/v1/memories/" and HAS_MEM0 and memory:
            user_id = query.get("user_id", ["default_user"])[0]
            agent_id = query.get("agent_id", [""])[0] or None
            limit = int(query.get("limit", ["10"])[0])
            
            try:
                results = memory.get_all(user_id=user_id, agent_id=agent_id, limit=limit)
                memories = []
                
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
                elif isinstance(results, dict) and "results" in results:
                    for mem in results["results"]:
                        memories.append({
                            "id": mem.get("id", str(uuid.uuid4())),
                            "content": mem.get("memory", mem.get("content", "")),
                            "user_id": user_id,
                            "metadata": mem.get("metadata", {}),
                            "created_at": mem.get("created_at", datetime.now().isoformat())
                        })
                
                self.send_json_response(memories)
            except Exception as e:
                print(f"[ERROR] Get memories failed: {e}")
                self.send_json_response({"error": str(e)}, 500)
            return
        
        self.send_json_response({"error": "Not found"}, 404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()
        data = json.loads(body) if body else {}
        
        # Embeddings endpoint
        if path == "/v1/embeddings":
            try:
                input_texts = data.get("input", [])
                if isinstance(input_texts, str):
                    input_texts = [input_texts]
                
                if not input_texts:
                    self.send_json_response({"error": "No input provided"}, 400)
                    return
                
                embeddings = model_manager.embed(input_texts)
                
                response = {
                    "object": "list",
                    "data": [
                        {
                            "object": "embedding",
                            "embedding": emb,
                            "index": i
                        }
                        for i, emb in enumerate(embeddings)
                    ],
                    "model": data.get("model", "nomic-embed-text-v1.5"),
                    "usage": {
                        "prompt_tokens": sum(len(t.split()) for t in input_texts),
                        "total_tokens": sum(len(t.split()) for t in input_texts)
                    }
                }
                
                self.send_json_response(response)
            except Exception as e:
                print(f"[ERROR] Embeddings failed: {e}")
                import traceback
                traceback.print_exc()
                self.send_json_response({"error": str(e)}, 500)
            return
        
        # Chat completions endpoint
        if path == "/v1/chat/completions":
            try:
                messages = data.get("messages", [])
                max_tokens = data.get("max_tokens", 512)
                
                if not messages:
                    self.send_json_response({"error": "No messages provided"}, 400)
                    return
                
                response_text = model_manager.chat(messages, max_tokens=max_tokens)
                
                response = {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": data.get("model", "lfm-2-vision-450m"),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response_text
                            },
                            "finish_reason": "stop"
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    }
                }
                
                self.send_json_response(response)
            except Exception as e:
                print(f"[ERROR] Chat completion failed: {e}")
                import traceback
                traceback.print_exc()
                self.send_json_response({"error": str(e)}, 500)
            return
        
        # Add memory
        if path == "/v1/memories/" and HAS_MEM0 and memory:
            try:
                messages = data.get("messages", [])
                user_id = data.get("user_id", "default_user")
                agent_id = data.get("agent_id")
                metadata = data.get("metadata", {})
                
                content = " ".join([m.get("content", "") for m in messages if m.get("content")])
                
                result = memory.add(
                    messages=messages,
                    user_id=user_id,
                    agent_id=agent_id,
                    metadata=metadata,
                    infer=False  # Skip LLM fact extraction for local models
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
                print(f"[ERROR] Add memory failed: {e}")
                import traceback
                traceback.print_exc()
                self.send_json_response({"error": str(e)}, 500)
            return
        
        # Search memories
        if path == "/v1/memories/search/" and HAS_MEM0 and memory:
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
                    if isinstance(r, dict):
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
                    elif isinstance(r, str):
                        search_results.append({
                            "memory": {
                                "id": str(uuid.uuid4()),
                                "content": r,
                                "user_id": user_id,
                                "metadata": {},
                                "created_at": datetime.now().isoformat()
                            },
                            "score": 1.0,
                            "distance": 0.0
                        })
                
                self.send_json_response(search_results)
            except Exception as e:
                print(f"[ERROR] Search failed: {e}")
                self.send_json_response({"error": str(e)}, 500)
            return
        
        self.send_json_response({"error": "Not found"}, 404)
    
    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path.startswith("/v1/memories/"):
            self.send_json_response({"deleted": True})
            return
        
        self.send_json_response({"error": "Not found"}, 404)


# ============================================================================
# Main
# ============================================================================

def main():
    """Main entry point."""
    
    # Check if models exist
    embedding_path = MODELS_DIR / "nomic-embed-text-v1.5"
    llm_path = MODELS_DIR / "lfm-2-vision-450m"
    
    if not embedding_path.exists() or not llm_path.exists():
        print("[ERROR] Models not found!")
        print()
        print("Please download the models first:")
        print("  python download_models.py")
        print()
        sys.exit(1)
    
    print("-" * 70)
    print("Available endpoints:")
    print(f"  Health:      GET  http://{HOST}:{PORT}/health")
    print(f"  Models:      GET  http://{HOST}:{PORT}/v1/models")
    print(f"  Embeddings:  POST http://{HOST}:{PORT}/v1/embeddings")
    print(f"  Chat:        POST http://{HOST}:{PORT}/v1/chat/completions")
    if HAS_MEM0:
        print(f"  Memories:    GET  http://{HOST}:{PORT}/v1/memories/")
        print(f"  Add Memory:  POST http://{HOST}:{PORT}/v1/memories/")
        print(f"  Search:      POST http://{HOST}:{PORT}/v1/memories/search/")
    print("-" * 70)
    print()
    print("Press Ctrl+C to stop")
    print()
    
    server = HTTPServer((HOST, PORT), Mem0LocalHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
