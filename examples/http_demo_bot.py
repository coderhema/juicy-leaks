"""Tiny deliberately vulnerable chatbot HTTP API for testing Juicy Leaks's HTTP target. FAKE data.

  python examples/http_demo_bot.py [--port 8088] [--live]

POST /chat {"message": "..."} -> {"reply": "..."}
Offline it uses Juicy Leaks's naive mock bot; with --live it runs bank_bot.yaml's system prompt on
the configured LLM provider.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from juicy_leaks.config import Settings  # noqa: E402
from juicy_leaks.llm import ChatClient  # noqa: E402
from juicy_leaks.targets import LLMTarget, MockTarget, Target  # noqa: E402

TARGET = Target.from_yaml(Path(__file__).with_name("bank_bot.yaml"))


def make_bot(live: bool):
    if not live:
        return MockTarget(TARGET)
    s = Settings.load(mock=False)
    return LLMTarget(TARGET, ChatClient(s.api_key, s.base_url, extra_body=s.extra_body), s.target_model)


def serve(port: int = 8088, live: bool = False):
    bot = make_bot(live)

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
            reply = bot.ask(str(body.get("message", "")))
            data = json.dumps({"reply": reply}).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    return srv


if __name__ == "__main__":
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8088
    print(f"Demo bot on http://127.0.0.1:{port}/chat")
    serve(port, "--live" in sys.argv).serve_forever()
