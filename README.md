# AI Chatbot Widget

Production-ready AI chatbot widget on AWS. A simple HTTP API backed by Lambda and Claude, with an embeddable JavaScript widget for customer-facing chat. Store conversation history in DynamoDB with automatic session expiration.

Built as a reference implementation by [Three Moons Network](https://threemoonsnetwork.net) — an AI consulting practice helping small businesses automate with production-grade systems.

## Architecture

```
                    ┌─────────────────────────────────────────────────┐
                    │                   AWS Cloud                     │
                    │                                                 │
  Web Browser        │  API Gateway (HTTP API)                        │
  (Website)   ────▶ │  POST /chat        GET /chat/{session_id}      │
               ◀──   │    │                       │                   │
                    │    ▼                       ▼                   │
                    │   Lambda Functions        Lambda Functions     │
                    │   (handle chat)           (retrieve history)   │
                    │    │                       │                   │
                    │    ▼                       ▼                   │
                    │  DynamoDB                                      │
                    │  Conversations table                           │
                    │  (with TTL: auto-expire)                       │
                    │    │                                           │
                    │    ▼                                           │
                    │  Claude API (via Anthropic SDK)                │
                    │  (inference)                                   │
                    │                                                 │
                    │  CloudWatch Logs + Alarms                      │
                    │  SSM Parameter Store (API keys, config)        │
                    └─────────────────────────────────────────────────┘

  /widget/index.html
  (Embeddable JavaScript)
  ├── widget.js        — Core chat widget logic
  ├── styles.css       — Widget styling
  └── example.html     — Demo page
```

## What It Does

1. **Chat API** — REST endpoints for sending messages and retrieving history
2. **Conversation Storage** — DynamoDB with TTL for automatic session cleanup
3. **Claude Integration** — Real-time inference with configurable system prompts
4. **Embeddable Widget** — Single `<script>` tag to embed chat anywhere
5. **CORS Configured** — Safe cross-origin requests from any domain

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Send a message, get AI response |
| `GET` | `/chat/{session_id}` | Get full conversation history |

### Request/Response Format

**POST /chat**

```bash
curl -X POST https://api-id.execute-api.region.amazonaws.com/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user-abc-123",
    "message": "How do I reset my password?"
  }'
```

Response:

```json
{
  "session_id": "user-abc-123",
  "user_message": "How do I reset my password?",
  "assistant_message": "To reset your password, go to...",
  "message_count": 3,
  "model": "claude-sonnet-4-20250514",
  "usage": {
    "input_tokens": 120,
    "output_tokens": 85
  }
}
```

**GET /chat/{session_id}**

```bash
curl https://api-id.execute-api.region.amazonaws.com/chat/user-abc-123
```

Response:

```json
{
  "session_id": "user-abc-123",
  "messages": [
    {
      "role": "user",
      "content": "How do I reset my password?",
      "timestamp": "2026-04-01T12:00:00Z"
    },
    {
      "role": "assistant",
      "content": "To reset your password, go to...",
      "timestamp": "2026-04-01T12:00:05Z"
    }
  ],
  "created_at": "2026-04-01T11:55:00Z",
  "expires_at": "2026-04-08T11:55:00Z"
}
```

## Quick Start

### Prerequisites

- AWS account with CLI configured
- Terraform >= 1.5
- Python 3.11+
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### 1. Clone and configure

```bash
git clone git@github.com:Three-Moons-Network/ai-chatbot-widget.git
cd ai-chatbot-widget
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit terraform.tfvars with your API key
```

### 2. Build Lambda package

```bash
./scripts/deploy.sh
```

### 3. Deploy infrastructure

```bash
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

Terraform outputs the API endpoint.

### 4. Embed the widget

Update `/widget/example.html` with your API endpoint, then:

```bash
# Serve the widget locally for testing
python3 -m http.server 8000 -d widget/
# Open http://localhost:8000/example.html
```

Or embed in your website:

```html
<div id="chat-widget"></div>
<script>
  window.ChatWidgetConfig = {
    apiEndpoint: "https://your-api-id.execute-api.us-east-1.amazonaws.com",
    sessionId: "user-" + Math.random().toString(36).substr(2, 9)
  };
</script>
<script src="https://your-domain.com/widget/widget.js"></script>
```

### 5. Tear down

```bash
terraform destroy
```

## Project Structure

```
├── src/
│   └── handler.py                    # Lambda handler for /chat endpoints
├── tests/
│   ├── test_handler.py               # Handler tests with moto
│   └── conftest.py                   # Shared fixtures
├── widget/
│   ├── widget.js                     # Core chat widget JavaScript
│   ├── styles.css                    # Widget styling
│   └── example.html                  # Demo page
├── terraform/
│   ├── main.tf                       # API Gateway, Lambda, DynamoDB, IAM
│   ├── variables.tf                  # Input variables
│   ├── outputs.tf                    # Outputs
│   ├── backend.tf                    # Remote state config
│   └── terraform.tfvars.example      # Example configuration
├── scripts/
│   └── deploy.sh                     # Build Lambda zip package
├── .github/workflows/
│   └── ci.yml                        # Test, lint, TF validate, package
├── requirements.txt                  # Runtime: anthropic, boto3
└── requirements-dev.txt              # Dev: pytest, moto, ruff
```

## Infrastructure Details

| Resource | Purpose |
|----------|---------|
| API Gateway (HTTP API v2) | REST endpoint with CORS enabled |
| Lambda (Python 3.11) | Handler for chat POST and GET operations |
| DynamoDB (conversations table) | Store messages with TTL for auto-cleanup |
| SSM Parameter Store | Anthropic API key (encrypted) |
| CloudWatch Log Groups | Lambda logs and API access logs |
| CloudWatch Alarms | Error count, latency warnings |
| IAM Role + Policy | Least-privilege: DynamoDB, SSM, logs |

All resources tagged with Project, Environment, ManagedBy, and Owner.

## Customization

**Change the AI system prompt:**

Edit the `SYSTEM_PROMPT` in `src/handler.py` to customize chatbot behavior.

**Configure conversation TTL:**

Edit `conversation_ttl_hours` in `terraform/terraform.tfvars` (default: 168 hours / 7 days).

**Style the widget:**

Edit `/widget/styles.css` to match your brand colors and layout.

**Switch Claude models:**

```bash
terraform plan -var="anthropic_model=claude-opus-4-20250514" -out=tfplan
```

## Cost Estimate

For moderate usage (100-1,000 messages/day):

| Component | Estimated Monthly Cost |
|-----------|----------------------|
| Lambda | ~$0-1 (free tier covers most workloads) |
| API Gateway | ~$0-1 (free tier: 1M requests) |
| DynamoDB | ~$0-5 (on-demand or provisioned) |
| CloudWatch | ~$0.50 (log storage) |
| Anthropic API | Usage-based (~$3/M input tokens, ~$15/M output tokens for Sonnet) |

**Total infrastructure: ~$1-7/month.** Your main cost is Anthropic API usage.

## Local Development

```bash
# Set up
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Lint
ruff check src/
ruff format src/

# Test handler locally
export ANTHROPIC_API_KEY="sk-ant-..."
python -c "
from src.handler import lambda_handler
import json
event = {
    'requestContext': {'http': {'method': 'POST'}},
    'body': json.dumps({'session_id': 'test-123', 'message': 'Hello'})
}
result = lambda_handler(event, None)
print(json.dumps(json.loads(result['body']), indent=2))
"
```

## Widget Embedding

The widget is a self-contained JavaScript bundle that:

- Injects a floating chat widget into the page
- Manages conversation state in `sessionStorage`
- Makes API calls to your Lambda endpoint
- Auto-reconnects on network failures
- Respects dark mode preferences via `prefers-color-scheme`

### Configuration Options

```javascript
window.ChatWidgetConfig = {
  // Required: API endpoint from terraform output
  apiEndpoint: "https://api-id.execute-api.us-east-1.amazonaws.com",

  // Required: Unique session identifier for this user
  sessionId: "user-123",

  // Optional: Default title
  title: "Chat Support",

  // Optional: Default greeting message
  greeting: "Hi! How can I help?",

  // Optional: Position on screen (bottom-right, bottom-left, top-right, top-left)
  position: "bottom-right",

  // Optional: Width in pixels
  width: 380,

  // Optional: Height in pixels
  height: 500
};
```

## Monitoring

CloudWatch metrics available:

- Lambda invocations, errors, duration
- API Gateway requests, latency, 4xx/5xx errors
- DynamoDB read/write capacity, throttling
- Conversation counts by hour

Access the dashboard:

```bash
aws cloudwatch get-dashboard --dashboard-name ai-chatbot-widget-dev
```

## License

MIT

## Author

Charles Harvey ([linuxlsr](https://github.com/linuxlsr)) — [Three Moons Network LLC](https://threemoonsnetwork.net)
