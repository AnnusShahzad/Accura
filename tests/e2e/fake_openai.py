"""
Minimal OpenAI-compatible /chat/completions server for local end-to-end
runs, so the browser suites need no real AI key.

    python3 tests/e2e/fake_openai.py        # listens on 127.0.0.1:8099

Point the backend at it with OPENAI_API_KEY=sk-fake and
OPENAI_BASE_URL=http://127.0.0.1:8099/v1 (or the CUSTOM_AI_* equivalents).
Like real reasoning models it rejects max_tokens for gpt-5* models.
"""

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KEYS = {"Bearer sk-fake", "Bearer sk-custom-123456789"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.headers.get("Authorization") not in KEYS:
            return self._send(401, {"error": {"message": "Incorrect API key provided"}})
        model = req["model"]
        if model.startswith("gpt-5") and "max_tokens" in req:
            return self._send(400, {"error": {"message": (
                "Unsupported parameter: 'max_tokens' is not supported with this model. "
                "Use 'max_completion_tokens' instead.")}})
        last = req["messages"][-1]["content"] or ""
        time.sleep(0.6)
        if "Evaluate the response" in last:
            content = '```json\n{"score": 88, "reasoning": "Accurate and clear."}\n```'
        elif "rephrase the original prompt" in last:
            content = "Please explain clearly"
        elif "generate a very short title" in last:
            content = "Photosynthesis Explained"
        else:
            turns = sum(1 for m in req["messages"] if m["role"] in ("user", "assistant"))
            content = (f"**Answer** from `{model}` (context messages: {turns}).\n\n"
                       "Plants turn light into chemical energy.\n\n$$E = mc^2$$\n\n"
                       "- light\n- water\n- carbon dioxide")
        self._send(200, {
            "id": "x", "object": "chat.completion", "created": 0, "model": model,
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 42, "completion_tokens": 17, "total_tokens": 59},
        })


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8099), Handler).serve_forever()
