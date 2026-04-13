import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Tuple


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _cost_of_wait(wait_days: float) -> str:
    if wait_days <= 7:
        return "low"
    if wait_days <= 30:
        return "medium"
    return "high"


def _validate_tool_arguments(args: Any) -> Tuple[Dict[str, Any], int]:
    if not isinstance(args, dict):
        return {"error": "arguments must be an object"}, 400

    required = ["item_name", "current_price", "expected_price", "wait_days", "urgent"]
    missing = [k for k in required if k not in args]
    if missing:
        return {"error": f"Missing required fields: {', '.join(missing)}"}, 400

    item_name = args["item_name"]
    if not isinstance(item_name, str) or not item_name.strip():
        return {"error": "item_name must be a non-empty string"}, 400

    try:
        current_price = float(args["current_price"])
        expected_price = float(args["expected_price"])
        wait_days = float(args["wait_days"])
    except (TypeError, ValueError):
        return {"error": "current_price, expected_price, and wait_days must be numbers"}, 400

    urgent = args["urgent"]
    if not isinstance(urgent, bool):
        return {"error": "urgent must be a boolean"}, 400

    return {
        "item_name": item_name,
        "current_price": current_price,
        "expected_price": expected_price,
        "wait_days": wait_days,
        "urgent": urgent,
    }, 200


def decide_buy_now_or_wait(args: Any) -> Tuple[Dict[str, Any], int]:
    validated, status = _validate_tool_arguments(args)
    if status != 200:
        return validated, status

    current_price = validated["current_price"]
    expected_price = validated["expected_price"]
    wait_days = validated["wait_days"]
    urgent = validated["urgent"]

    savings = current_price - expected_price

    if urgent:
        decision = "buy_now"
        reason = "urgent is true, so buy_now"
    elif savings >= 300 and wait_days <= 30:
        decision = "wait"
        reason = "savings >= 300 and wait_days <= 30, so wait"
    else:
        decision = "buy_now"
        reason = "conditions for wait not met, so buy_now"

    result = {
        "decision": decision,
        "reason": reason,
        "saving": savings,
        "cost_of_wait": _cost_of_wait(wait_days),
    }
    return result, 200


class MCPHandler(BaseHTTPRequestHandler):
    server_version = "BuyNowOrWaitMCP/0.1"

    def do_GET(self) -> None:
        if self.path == "/health":
            _json_response(self, 200, {"status": "ok"})
            return
        _json_response(self, 404, {"error": "Not found"})

    def do_POST(self) -> None:
        if self.path != "/mcp":
            _json_response(self, 404, {"error": "Not found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)

        try:
            req = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            _json_response(
                self,
                400,
                {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
            )
            return

        request_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "buy-now-or-wait", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            }
            _json_response(self, 200, {"jsonrpc": "2.0", "id": request_id, "result": result})
            return

        if method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "decide_buy_now_or_wait",
                        "description": "Decide whether the user should buy now or wait based on current price, expected future price, wait days, and urgency.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "item_name": {"type": "string"},
                                "current_price": {"type": "number"},
                                "expected_price": {"type": "number"},
                                "wait_days": {"type": "number"},
                                "urgent": {"type": "boolean"},
                            },
                            "required": ["item_name", "current_price", "expected_price", "wait_days", "urgent"],
                            "additionalProperties": False,
                        },
                    }
                ]
            }
            _json_response(self, 200, {"jsonrpc": "2.0", "id": request_id, "result": result})
            return

        if method == "tools/call":
            if not isinstance(params, dict):
                _json_response(
                    self,
                    200,
                    {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "params must be an object"}},
                )
                return

            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name != "decide_buy_now_or_wait":
                _json_response(
                    self,
                    200,
                    {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Unknown tool"}},
                )
                return

            tool_result, status = decide_buy_now_or_wait(arguments)
            if status != 200:
                _json_response(
                    self,
                    200,
                    {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": tool_result["error"]}},
                )
                return

            _json_response(
                self,
                200,
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(tool_result, separators=(",", ":"))}],
                        "structuredContent": tool_result,
                    },
                },
            )
            return

        _json_response(
            self,
            200,
            {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}},
        )


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), MCPHandler)
    print(f"Serving buy-now-or-wait MCP on 0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
