# Screen Memory Assistant

An AI-powered screen capture and memory system that learns who you are and understands your context using local LLM (Liquid 450M via LM Studio) and Mem0 for memory embeddings.

## Features

- **Periodic Screen Capture**: Configurable interval screenshots with compression
- **Vision AI**: Analyzes screen content using local LLM
- **Memory System**: Stores context and activities using Mem0 embeddings
- **Cross-Platform**: Optimized for macOS, works on Windows
- **Resource Efficient**: JPEG compression, image resizing, async processing

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Screen    │────▶│   Resized    │────▶│    LLM      │
│   Capture   │     │   (1024px)   │     │   Vision    │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Search    │◀────│    Mem0      │◀────│   Context   │
│   Memory    │     │   Vector DB  │     │   Store     │
└─────────────┘     └──────────────┘     └─────────────┘
```

## Prerequisites

### 1. Go 1.21+
Install from https://go.dev/dl/

### 2. LM Studio
- Download: https://lmstudio.ai/
- Load your Liquid 450M model (or any vision-capable model)
- Start the local server (default: http://localhost:1234)

### 3. Mem0 Server

Mem0 requires a REST API server. We've included `mem0_server.py` that uses LM Studio for local embeddings:

```bash
# Install dependencies
pip install mem0ai requests

# Start the Mem0 server (in a separate terminal)
python mem0_server.py
```

Mem0 server will start on http://localhost:8000

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd screen-memory-assistant

# Install Mem0 (Python required)
pip install mem0ai

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
  max_width: 1024         # Resize to max width
  enabled: true

# LM Studio
llm:
  base_url: "http://localhost:1234/v1"
  model: "local-model"
  max_tokens: 512
  temperature: 0.7

# Mem0
memory:
  base_url: "http://localhost:8000"
  user_id: "default_user"
  collection_name: "screen_memories"
```

### Environment Variables
- `LM_STUDIO_URL`: Override LM Studio endpoint
- `MEM0_URL`: Override Mem0 endpoint
- `MEM0_API_KEY`: API key for Mem0 (if using cloud)

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
2. **Resizes** image to max 1024px width (preserves aspect ratio)
3. **Compresses** to JPEG (85% quality by default)
4. **Sends to LLM** for vision analysis
5. **Stores in Mem0** with metadata (context, activities, intent)
6. **Builds context** over time to understand you better

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

- **Image resizing**: Downsamples to 1024px max before sending
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
│   ├── memory/               # Mem0 integration
│   └── service/              # Orchestrator
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

### "Mem0 not available"
- Start Mem0 server: `mem0 server`
- Check the URL in config
- Verify port 8000 is free

## License

MIT
