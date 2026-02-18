#!/usr/bin/env python3
"""Quick test to verify Mem0 configuration works."""

import os
import sys
import requests

HOST = os.getenv("MEM0_HOST", "localhost")
PORT = int(os.getenv("MEM0_PORT", "8000"))
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")

print("="*60)
print("Mem0 Configuration Test")
print("="*60)

try:
    resp = requests.get(f"{LM_STUDIO_URL}/models", timeout=5)
    if resp.status_code == 200:
        models = resp.json().get("data", [])
        print(f"[OK] LM Studio connected at {LM_STUDIO_URL}")
        print(f"     Models loaded: {len(models)}")
        for m in models[:3]:
            print(f"       - {m['id']}")
        if len(models) > 3:
            print(f"       ... and {len(models)-3} more")
    else:
        print(f"[WARN] LM Studio returned status {resp.status_code}")
except Exception as e:
    print(f"[FAIL] Cannot connect to LM Studio: {e}")
    sys.exit(1)

from mem0 import Memory

print()
print("Testing Mem0 configuration...")

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
        "provider": "openai",
        "config": {
            "model": "text-embedding-nomic-embed-text-v1.5",
            "api_key": "not-needed",
            "openai_base_url": LM_STUDIO_URL,
        }
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": "l3-8b-stheno-v3.2@q4_k_s",
            "api_key": "not-needed",
            "openai_base_url": LM_STUDIO_URL,
            "temperature": 0.1,
            "max_tokens": 256,
        }
    }
}

try:
    memory = Memory.from_config(config_dict=config)
    print("[OK] Mem0 initialized successfully!")
    print()
    print("Test passed! The server should start correctly now.")
except Exception as e:
    print(f"[FAIL] Failed to initialize Mem0: {e}")
    sys.exit(1)
