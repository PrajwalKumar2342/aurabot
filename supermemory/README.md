# Screen Memory Assistant - Supermemory Edition

An AI-powered screen capture and memory system that learns who you are and understands your context using local LLM (Liquid 450M via LM Studio) and **Supermemory.ai** for cloud memory storage.

## Features

- **Periodic Screen Capture**: Configurable interval screenshots with compression
- **Vision AI**: Analyzes screen content using local LLM
- **Memory System**: Stores context and activities using Supermemory.ai cloud embeddings
- **Cross-Platform**: Optimized for macOS, works on Windows
- **Resource Efficient**: JPEG compression, async processing
- **Cloud-Powered Memory**: Uses Supermemory.ai for scalable, persistent memory storage

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Screen    │────▶│  Compressed  │────▶│    LLM      │
│   Capture   │     │    (JPEG)    │     │   Vision    │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Search    │◀────│ Supermemory  │◀────│   Context   │
│   Memory    │     │   Cloud API  │     │   Store     │
└─────────────┘     └──────────────┘     └─────────────┘
```

## Prerequisites

### 1. Go 1.21+
Install from https://go.dev/dl/

### 2. Supermemory.ai Account
- Sign up at https://supermemory.ai
- Get your API key from the Developer Platform
- Set the `SUPERMEMORY_API_KEY` environment variable

### 3. LLM Backend (Choose one)

#### Option A: Local Models (No External Dependencies) ⭐ Recommended
Run models completely locally without LM Studio or external APIs.

**Quick Setup:**
```bash
# Windows
setup_local_models.bat

# Linux/macOS
chmod +x setup_local_models.sh
./setup_local_models.sh
```

Or manually:
```bash
# Install dependencies
pip install -r requirements.txt

# Download models (one-time)
python download_models.py

# Start the server
python local_model_server.py   # API only
# OR
python supermemory_local.py     # Full Supermemory integration
```

**Models included:**
- `LFM-2-Vision-450M` - Vision-language model for chat and image understanding
- `Nomic-Embed-Text-v1.5` - Text embeddings for memory/search

See [LOCAL_MODELS.md](LOCAL_MODELS.md) for detailed documentation.

#### Option B: LM Studio
- Download: https://lmstudio.ai/
- Load your Liquid 450M model (or any vision-capable model)
- Start the local server (default: http://localhost:1234)

### 4. Supermemory Server

Supermemory requires a REST API server. Choose one:

**With Local Models:**
```bash
pip install supermemory requests
python supermemory_local.py
```

**With LM Studio:**
```bash
pip install supermemory requests
python supermemory_server.py
```

Supermemory server will start on http://localhost:8000

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd supermemory

# Install Supermemory SDK (Python required)
pip install supermemory

# Download Go dependencies
go mod download

# Build
make build

# Or build for specific platform
make build-macos
make build-windows
```

## Configuration

Edit `config.yaml` or set environment variables:

```yaml
# Screen capture
capture:
  interval_seconds: 30    # How often to capture
  quality: 85             # JPEG quality (1-100)
  enabled: true

# LM Studio
llm:
  base_url: "http://localhost:1234/v1"
  model: "local-model"
  max_tokens: 512
  temperature: 0.7

# Supermemory
memory:
  api_key: ""                   # Your Supermemory API key
  base_url: "http://localhost:8000"  # Supermemory server URL
  user_id: "default_user"
  collection_name: "screen_memories"
```

### Environment Variables
- `LM_STUDIO_URL`: Override LM Studio endpoint
- `SUPERMEMORY_URL`: Override Supermemory endpoint
- `SUPERMEMORY_API_KEY`: Your Supermemory API key (required)
- `CEREBRAS_API_KEY`: Optional Cerebras API key for better LLM responses

## Usage

### Start the Service

```bash
# Run directly
go run .

# Or use make
make run

# With verbose logging
make dev
```

### How It Works

1. **Captures screen** every N seconds (configurable)
2. **Compresses** to JPEG (85% quality by default)
3. **Sends to LLM** for vision analysis
4. **Stores in Supermemory** with metadata (context, activities, intent)
5. **Builds context** over time to understand you better

### Chat with Context

The service maintains a memory of your activities. You can query it:

```go
response, err := svc.Chat(ctx, "What was I working on earlier?")
```

## Testing

```bash
# Run all tests
make test

# With coverage
make test-coverage
```

## Resource Optimization

- **JPEG compression**: Reduces payload size significantly
- **Async processing**: Non-blocking capture and analysis
- **Configurable intervals**: Balance between insight and resource usage

## Project Structure

```
.
├── main.go                    # Entry point
├── config.yaml                # Configuration
├── go.mod                     # Go dependencies
├── Makefile                   # Build commands
├── internal/
│   ├── config/               # Configuration management
│   ├── capture/              # Screen capture (cross-platform)
│   ├── llm/                  # LM Studio client
│   ├── memory/               # Supermemory integration
│   └── service/              # Orchestrator
├── download_models.py         # Download local models
├── local_model_server.py      # Standalone local model server
├── supermemory_local.py       # Supermemory with local models
├── supermemory_server.py      # Supermemory REST API server
├── setup_local_models.bat     # Windows setup script
├── setup_local_models.sh      # Linux/macOS setup script
├── LOCAL_MODELS.md            # Local models documentation
└── README.md
```

## Platform Notes

### macOS
- Optimized for macOS
- Requires screen recording permission
- Go to System Preferences > Security & Privacy > Screen Recording

### Windows
- Requires Windows 10/11
- May need graphics drivers for screenshot library

## Troubleshooting

### "No active displays found"
- Check display permissions
- Restart the application

### "LLM not available"
- Verify LM Studio is running
- Check the URL in config
- Ensure a model is loaded

### "Supermemory not available"
- Start Supermemory server: `python supermemory_server.py`
- Check the URL in config
- Verify port 8000 is free
- Ensure `SUPERMEMORY_API_KEY` is set

### "Authentication failed"
- Verify your Supermemory API key is correct
- Check that `SUPERMEMORY_API_KEY` environment variable is set

## License

MIT
