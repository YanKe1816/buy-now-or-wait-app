# Buy Now or Wait (Python MCP Task App)

Minimal deterministic MCP server for a ChatGPT Task App.

## Endpoints
- `GET /health`
- `POST /mcp`

## Supported MCP JSON-RPC methods
- `initialize`
- `tools/list`
- `tools/call`

## Tool
- **name:** `decide_buy_now_or_wait`
- **description:** Decide whether the user should buy now or wait based on current price, expected future price, wait days, and urgency.

### Input
```json
{
  "item_name": "string",
  "current_price": 1200,
  "expected_price": 800,
  "wait_days": 14,
  "urgent": false
}
```

### Output
```json
{
  "decision": "buy_now | wait",
  "reason": "short deterministic explanation",
  "saving": 400,
  "cost_of_wait": "low | medium | high"
}
```

## Deterministic decision logic
1. If `urgent` is `true` → `buy_now`
2. Else if `expected savings >= 300` and `wait_days <= 30` → `wait`
3. Else → `buy_now`

## Local quickstart
```bash
python3 server.py
```

With custom port:
```bash
PORT=8080 python3 server.py
```

## Quick validation
Health check:
```bash
curl -s http://localhost:8000/health
```

List tools:
```bash
curl -s http://localhost:8000/mcp \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

Call tool:
```bash
curl -s http://localhost:8000/mcp \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"decide_buy_now_or_wait","arguments":{"item_name":"Laptop","current_price":1500,"expected_price":1100,"wait_days":14,"urgent":false}}}'
```
