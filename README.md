# Payment Reconciliation API

LLM-driven intelligent payment reconciliation service for gaming platforms.

## Features

- **Format Adaptation**: LLM automatically detects and adapts to file format changes
- **Intelligent Analysis**: AI-powered anomaly detection and recommendations
- **Multiple Channels**: Support for multiple payment channels (BOSSPAY, antpay, apppay, etc.)
- **Multi-Model Support**: Uses OpenRouter API - supports Claude, GPT-4, and more
- **Cloud Ready**: Dockerized deployment for Railway, AWS, GCP, etc.

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key (OpenRouter)
export OPENROUTER_API_KEY="sk-or-v1-..."

# Or use your OpenRouter key
export OPENROUTER_API_KEY="your-openrouter-key"

# Run server
uvicorn app.main:app --reload
```

### Docker

```bash
# Build image
docker build -t reconcile-payment .

# Run container
docker run -p 8000:8000 -e OPENROUTER_API_KEY=sk-or-v1-... reconcile-payment
```

## API Usage

### Reconcile Payments

```bash
curl -X POST "http://localhost:8000/api/v1/reconcile" \
  -F "deposit=@deposit.xlsx" \
  -F "withdraw=@withdraw.xlsx" \
  -F "channels=@bosspay.csv" \
  -F "channels=@antpay.csv" \
  -F "adapt=true" \
  -F "analyze=true"
```

### Response

```json
{
  "success": true,
  "file_check": {
    "needs_adaptation": false
  },
  "data": {
    "summary": {
      "total_deposit": {"count": 100, "matched": 98},
      "total_withdraw": {"count": 20, "matched": 20}
    },
    "channels": {...},
    "mismatched": [...],
    "missing_in_channel": [...]
  },
  "analysis": "对账结果分析报告..."
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key (get one at https://openrouter.ai) |
| `LLM_MODEL` | No | Model to use (default: anthropic/claude-sonnet-4-20250514) |
| `PORT` | No | Service port (default: 8000) |

### Supported Models

The service uses OpenRouter, which supports:
- `anthropic/claude-sonnet-4-20250514`
- `anthropic/claude-3.5-sonnet`
- `openai/gpt-4o`
- `google/gemini-pro-1.5`
- And many more: https://openrouter.ai/models

## Railway Deployment

1. Create new project on Railway
2. Connect this GitHub repository
3. Add `OPENROUTER_API_KEY` as environment variable
4. (Optional) Add volume mount for `/app/storage` for persistence
5. Deploy!

## Project Structure

```
app/
├── core/           # Core reconciliation logic
├── services/       # Business logic services
├── api/            # API routes
├── utils/          # Utilities (LLM client, storage)
└── main.py         # Application entry point
storage/            # File storage directory
```

## License

MIT
