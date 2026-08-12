"""
stub_llm_server.py — Stdlib HTTP OpenAI/vLLM compatible stub server on port 8100.
Zero external dependencies (uses http.server).
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class StubLLMHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {"data": [{"id": "qwen3.6-35b-a3b-nvfp4"}]}
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)
        try:
            body = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            body = {}

        rf = body.get("response_format")
        if rf and rf.get("type") == "json_schema":
            schema = rf.get("json_schema", {}).get("schema", {})
            props = schema.get("properties", {})
            canned = {k: None for k in props}
            content_str = json.dumps(canned)
        else:
            content_str = "42"

        response = {
            "choices": [{
                "message": {"content": content_str, "reasoning": "stub reasoning trace"},
                "finish_reason": "stop"
            }]
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def log_message(self, format, *args):
        pass  # Suppress HTTP log messages

def run_server(port=8100):
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, StubLLMHandler)
    print(f"Stub LLM Server listening on http://127.0.0.1:{port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
