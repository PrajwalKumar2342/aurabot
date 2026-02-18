# Migration Guide: Mem0 to Supermemory

This guide explains how to migrate from the Mem0-based screen memory assistant to the Supermemory.ai-based version.

## Key Differences

| Feature | Mem0 Version | Supermemory Version |
|---------|--------------|---------------------|
| Memory Provider | Local Qdrant + mem0ai | Supermemory.ai cloud |
| Embeddings | Local (Nomic/LM Studio) | Handled by Supermemory |
| Vector Store | Local Qdrant | Supermemory cloud |
| Authentication | Optional local | Required API key |
| Scalability | Single machine | Cloud-scalable |
| Setup Complexity | Higher (local Qdrant) | Lower (cloud service) |

## Migration Steps

### 1. Get Supermemory API Key

1. Sign up at https://supermemory.ai
2. Go to Developer Platform → API Keys
3. Create a new API key
4. Copy the API key for use in configuration

### 2. Update Environment Variables

Replace mem0 environment variables with Supermemory equivalents:

**Before (mem0):**
```bash
export MEM0_URL=http://localhost:8000
export MEM0_API_KEY=  # Optional for local
```

**After (supermemory):**
```bash
export SUPERMEMORY_URL=http://localhost:8000
export SUPERMEMORY_API_KEY=your_api_key_here  # Required
```

### 3. Update Configuration File

**Before (config.yaml):**
```yaml
memory:
  api_key: ""                   # Optional
  base_url: "http://localhost:8000"
  user_id: "default_user"
  collection_name: "screen_memories"
```

**After (config.yaml):**
```yaml
memory:
  api_key: "your_api_key"       # Required
  base_url: "http://localhost:8000"
  user_id: "default_user"
  collection_name: "screen_memories"
```

### 4. Install Dependencies

**Before:**
```bash
pip install mem0ai requests
```

**After:**
```bash
pip install supermemory requests
```

### 5. Update Go Module (if building from source)

If you were importing the mem0 version as a dependency, update to the supermemory version:

```go
// Before
import "screen-memory-assistant/internal/memory"

// After
import "screen-memory-supermemory/internal/memory"
```

### 6. Run the New Server

**Before:**
```bash
python mem0_server.py
```

**After:**
```bash
python supermemory_server.py
```

Or with local models:
```bash
python supermemory_local.py
```

## API Compatibility

The Supermemory version maintains API compatibility with the mem0 version:

- `GET /health` - Health check
- `GET /v1/memories/` - Get all memories
- `POST /v1/memories/` - Add a memory
- `POST /v1/memories/search/` - Search memories
- `DELETE /v1/memories/{id}` - Delete a memory

The request/response formats are the same, so existing clients should work without modification.

## Data Migration

Currently, there is no automatic migration for existing memories stored in Qdrant. Options:

1. **Start fresh**: Let the new system build up memories over time
2. **Manual export/import**: Export memories from Qdrant and import them via the API
3. **Dual run**: Run both systems in parallel during transition

## Troubleshooting

### "SUPERMEMORY_API_KEY not set"
- Ensure you have set the `SUPERMEMORY_API_KEY` environment variable
- Check that your `.env` file is properly loaded
- Verify the API key is valid at https://supermemory.ai

### "Authentication failed"
- Check that your API key is correct
- Ensure the API key hasn't expired
- Verify you're using the correct API endpoint

### "Supermemory not available"
- Check that the Supermemory server is running
- Verify the `SUPERMEMORY_URL` is correct
- Ensure port 8000 is not blocked by a firewall

### Memory not persisting
- Supermemory uses `container_tag` instead of `agent_id` internally
- Ensure your `collection_name` in config matches expected values
- Check the server logs for detailed error messages

## Feature Comparison

### What's the Same
- Screen capture functionality
- LLM vision analysis
- Chat interface
- Configuration file format
- REST API endpoints
- Go application structure

### What's Different
- Memory storage backend (Qdrant → Supermemory.ai)
- Authentication requirements (optional → required)
- Embedding generation (local → cloud)
- Vector search implementation (local → cloud)
- Python package (mem0ai → supermemory)

## Benefits of Supermemory

1. **No local database**: No need to manage Qdrant
2. **Cloud scalability**: Memories are accessible from anywhere
3. **Better search**: Advanced hybrid search with reranking
4. **Less maintenance**: Managed cloud service
5. **User profiles**: Automatic profile building

## Rollback Plan

If you need to rollback to mem0:

1. Stop the supermemory server
2. Restore your original config.yaml
3. Start the mem0 server
4. Update environment variables back to MEM0_* equivalents

## Support

For Supermemory-specific issues:
- Documentation: https://supermemory.ai/docs
- API Reference: https://supermemory.ai/docs/memory-api
- Issues: Check the Supermemory GitHub or Discord

For this screen memory assistant:
- Check the README.md in this directory
- Review the LOCAL_MODELS.md for local setup help
