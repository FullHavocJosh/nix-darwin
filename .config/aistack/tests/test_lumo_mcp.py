"""Tests for .config/lumo/lumo_mcp.py (web research for interactive Claude Code). No network: a stub tamer on loopback.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_lumo_mcp.py
"""
import http.server
import json
import os
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SERVER = os.path.join(ROOT, ".config", "lumo", "lumo_mcp.py")

FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


SEEN = []


class Tamer(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append({"auth": self.headers.get("Authorization"), "body": body})
        msgs = body["messages"]
        if "MEMORY" in msgs[0]["content"] and (len(msgs) == 1 or "ALWAYS" in msgs[0]["content"]):
            content = "Answer: As of my last update the version was 1.0. No source found."
        else:
            content = "- Answer: yes\n- Links: https://example.org/doc"
        out = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


httpd = http.server.HTTPServer(("127.0.0.1", 0), Tamer)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{httpd.server_port}/v1"


def call(reqs, **env):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("AISTACK_", "AINFO_", "LUMO_MCP_"))}
    e.update({"AISTACK_DIR": os.path.join(ROOT, ".config", "aistack"), "AINFO_DIR": os.path.join(ROOT, ".config", "ainfo"), **env})
    p = subprocess.run([sys.executable, SERVER], input="\n".join(json.dumps(r) for r in reqs) + "\n",
                       capture_output=True, text=True, env=e, timeout=60)
    return [json.loads(l) for l in p.stdout.splitlines() if l.strip()]


print("protocol")
r = call([{"jsonrpc": "2.0", "id": 1, "method": "initialize"}, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])
check("initialize carries the WebSearch instructions", "WebSearch is disabled" in r[0]["result"]["instructions"], r[0])
check("tools/list offers lumo_search only", [t["name"] for t in r[1]["result"]["tools"]] == ["lumo_search"], r[1])
check("the tool asks Claude Code to load it upfront", r[1]["result"]["tools"][0].get("_meta", {}).get("anthropic/alwaysLoad") is True, r[1])

print("search")
secret = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
r = call([{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "lumo_search", "arguments": {
    "question": f"Why does my token {secret} fail with gh?", "context": "tried gh auth status"}}}],
    AISTACK_TAMER_URL=url, AISTACK_TAMER_KEY="k1")
res = r[0]["result"]
check("answer comes back with the endpoint it came from", not res["isError"] and "example.org/doc" in res["content"][0]["text"] and url in res["content"][0]["text"], res)
sent = SEEN[-1]["body"]["messages"][0]["content"] if SEEN else ""
check("the tamer key is sent as a bearer token", SEEN and SEEN[-1]["auth"] == "Bearer k1", SEEN[-1:] )
check("secrets are redacted before the question leaves the machine", secret not in sent and "QUESTION" in sent, sent[:300])
check("context is passed along", "tried gh auth status" in sent, sent[-200:])
check("Lumo is told the date and to use web_search", "web_search" in sent and __import__("time").strftime("%Y-%m-%d") in sent, sent[:300])

print("retry")
n = len(SEEN)
r = call([{"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "lumo_search", "arguments": {"question": "MEMORY test"}}}],
         AISTACK_TAMER_URL=url, AISTACK_TAMER_KEY="k1")
txt = r[0]["result"]["content"][0]["text"]
check("an answer from memory is retried once and the searched answer kept",
      len(SEEN) - n == 2 and "example.org/doc" in txt and "after one retry" in txt and "WARNING" not in txt, txt)
check("the retry insists on web_search", "web_search" in SEEN[-1]["body"]["messages"][-1]["content"], SEEN[-1])
n = len(SEEN)
r = call([{"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "lumo_search", "arguments": {"question": "MEMORY ALWAYS"}}}],
         AISTACK_TAMER_URL=url, AISTACK_TAMER_KEY="k1")
txt = r[0]["result"]["content"][0]["text"]
check("still from memory after the retry: a warning to check with WebFetch", len(SEEN) - n == 2 and "WARNING" in txt and "WebFetch" in txt, txt)
n = len(SEEN)
call([{"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "lumo_search", "arguments": {"question": "normal"}}}],
     AISTACK_TAMER_URL=url, AISTACK_TAMER_KEY="k1")
check("a searched answer is not retried", len(SEEN) - n == 1)

print("failures")
r = call([{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "lumo_search", "arguments": {"question": " "}}}])
check("an empty question is refused", r[0]["result"]["isError"] and "question is required" in r[0]["result"]["content"][0]["text"], r)
r = call([{"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "lumo_search", "arguments": {"question": "x"}}}],
         AISTACK_TAMER_URL="http://127.0.0.1:9/v1")
check("an unreachable Lumo is an error with a hint", r[0]["result"]["isError"] and "lumoreauth" in r[0]["result"]["content"][0]["text"], r)
n = len(SEEN)
r = call([{"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "lumo_search", "arguments": {"question": "x"}}}],
         AISTACK_TAMER_URL=url, AINFO_DIR="/nonexistent")
check("without the redaction helper nothing is sent", r[0]["result"]["isError"] and len(SEEN) == n and "nothing was sent" in r[0]["result"]["content"][0]["text"], r)

httpd.shutdown()
print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
