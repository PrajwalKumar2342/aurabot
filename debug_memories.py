import os
os.chdir('E:/Codes/embeddings')

from mem0 import Memory

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
            "openai_base_url": "http://localhost:1234/v1",
        }
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": "lfm2-vl-450m",
            "api_key": "not-needed",
            "openai_base_url": "http://localhost:1234/v1",
            "temperature": 0.1,
            "max_tokens": 256,
        }
    }
}

memory = Memory.from_config(config_dict=config)

# Check what get_all returns
results = memory.get_all(user_id="default_user", agent_id="screen_memories", limit=10)
print(f"Type: {type(results)}")
print(f"Content: {results}")
