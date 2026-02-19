# AuraBot Browser Extension

This browser extension connects your AI chat interfaces (ChatGPT, Claude, Gemini, Perplexity) with your AuraBot desktop app to enhance prompts using your saved memories.

## Features

- **Automatic Memory Enhancement**: Click the "Enhance" button to enrich your prompts with relevant memories
- **Multi-Platform Support**: Works on ChatGPT, Claude, Gemini, and Perplexity
- **Context-Aware**: Automatically finds memories related to your current prompt
- **Privacy-First**: All processing happens locally through your AuraBot app

## Installation

### 1. Install the Extension (Chrome/Edge)

1. Open Chrome/Edge and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `aurabot/extension/chrome` folder
5. The extension icon should appear in your toolbar

### 2. Start AuraBot App

The extension requires the AuraBot desktop app to be running. Start the app and ensure it's connected to your memory store.

### 3. Use on AI Websites

Visit any supported AI chat platform:
- ChatGPT (chat.openai.com or chatgpt.com)
- Claude (claude.ai)
- Gemini (gemini.google.com)
- Perplexity (perplexity.ai)

You'll see an "Enhance" button next to the input field. Click it to enhance your prompt with relevant memories.

## How It Works

1. **Type your prompt** in any supported AI chat interface
2. **Click "Enhance"** before sending
3. The extension sends your prompt to the AuraBot app via local HTTP API
4. AuraBot searches your memory store for relevant context
5. The enhanced prompt (with memory context) replaces your original text
6. **Send the enhanced prompt** to the AI

## API Endpoints

The AuraBot app exposes these endpoints for the extension:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Check if app is running |
| `/api/enhance` | POST | Enhance a prompt with memories |
| `/api/memories/search` | GET | Search memories by query |
| `/api/status` | GET | Get service status |

### Example: Enhance Prompt

```bash
curl -X POST http://localhost:7345/api/enhance \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Help me with this code",
    "context": "chatgpt",
    "max_memories": 5
  }'
```

Response:
```json
{
  "original_prompt": "Help me with this code",
  "enhanced_prompt": "Help me with this code\n\n[Context from previous sessions]\nBased on my previous activities:\n- Working on Go backend service...",
  "memories_used": ["..."],
  "memory_count": 2,
  "enhancement_type": "contextual"
}
```

## Troubleshooting

### Extension shows "AuraBot is offline"

- Make sure the AuraBot desktop app is running
- Check that the app is configured to enable the extension API (default port: 7345)
- Verify no firewall is blocking localhost:7345

### "Enhance" button not appearing

- Refresh the page after installing the extension
- Check that you're on a supported website
- Try disabling other extensions that might interfere

### No memories found

- Ensure screen capture is enabled and working
- Check that memories are being stored (view in app)
- Try a more specific prompt that relates to your saved memories

## Development

To modify the extension:

1. Edit files in `aurabot/extension/chrome/`
2. Go to `chrome://extensions/`
3. Click the refresh icon on the AuraBot extension card
4. Test your changes

## Files

```
extension/
├── chrome/
│   ├── manifest.json       # Extension manifest
│   ├── content.js          # Content script (injects button)
│   ├── styles.css          # Button & notification styles
│   ├── popup.html          # Extension popup UI
│   ├── popup.js            # Popup logic
│   └── icons/              # Extension icons
└── README.md               # This file
```
