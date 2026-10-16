#!/usr/bin/env python3
"""lumo MCP server: web research for interactive Claude Code through Lumo (lumo-tamer), registered from
.config/mcp/claude-desktop-mcp.json. The built-in WebSearch is denied in ~/.claude/settings.json (see
claudeSettingsCleanup in nix-modules/macos/packages-tui.nix), so a web question costs one tool call that returns a
sourced answer, instead of a chain of WebSearch and WebFetch turns that each re-read the whole conversation.

One tool:
  lumo_search(question, context)   one Lumo call; returns its answer with the URLs it found

Lumo is reached the same way aidev and ainfo reach it (ralph_mcp.tamer_endpoints: this machine's tamer, then
MacMiniM1's, then lumo.rollet.family). The question is passed through ainfo's secret redaction before it leaves the
machine; if that cannot be loaded, nothing is sent. Stdlib only.
"""

import importlib.util
import json
import os
import sys
import time
import urllib.request

AISTACK_DIR = os.environ.get("AISTACK_DIR") or os.path.expanduser("~/.config/aistack")
AINFO_DIR = os.environ.get("AINFO_DIR") or os.path.expanduser("~/.config/ainfo")
TIMEOUT_S = int(os.environ.get("LUMO_MCP_TIMEOUT_S", "300"))
REPLY_MAX = int(os.environ.get("LUMO_MCP_REPLY_CHARS", "12000"))
QUESTION_MAX = 4000
PROTOCOL = "2024-11-05"

PROMPT = """You are the web-research tool of a coding assistant. Today is {today}. Use your web_search tool before
answering: do not answer from memory, your training data is older than the question.
Prefer official documentation, release notes, man pages, registry pages and the project's own GitHub issues. Name the
product version when it matters.

Reply in this shape:
- Answer: what the sources say, in a few sentences. Quote the relevant sentence exactly, in quotation marks, when short.
- Links: the exact URLs you actually found, one per line, with a few words on what each page covers.
If you found nothing reliable, write "No source found" and do not guess. Never invent URLs, versions, flags or quotes.

QUESTION:
{question}
{context}"""

INSTRUCTIONS = (
    "Web search goes through lumo_search: the built-in WebSearch is disabled. Ask one specific question per call and "
    "put what you already know in context. Use WebFetch only to read one exact URL you already have (for example a "
    "link lumo_search returned), and context7 for library documentation. Lumo can miss documented features: when it "
    "answers 'No source found' for something that has official docs, WebFetch the official docs page directly."
)


def load(name, directory):
    spec = importlib.util.spec_from_file_location(name, os.path.join(directory, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Signs that Lumo answered from its training data instead of a web search.
MEMORY_SIGNS = ("no source found", "training data", "knowledge cutoff", "as of my last", "my last update",
                "without a live search", "cannot confirm", "real-time", "i don't have access", "i do not have access")
RETRY = ("That answer did not come from a web search. Run your web_search tool now for the question above and answer "
         "only from what it returns, with the exact URLs. If the search finds nothing, say \"No source found\".")


def from_memory(reply):
    low = reply.lower()
    return "http" not in low or any(s in low for s in MEMORY_SIGNS)


def ask(base, key, messages):
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": os.environ.get("LUMO_MCP_MODEL", "lumo"), "messages": messages}).encode(),
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {key}"} if key else {})},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return json.load(r)["choices"][0]["message"].get("content") or ""


def lumo_search(a):
    question = str(a.get("question") or "").strip()
    if not question:
        return {"ok": False, "error": "question is required"}
    context = str(a.get("context") or "").strip()
    try:
        redact = load("ainfo_mcp", AINFO_DIR).redact
        endpoints = load("ralph_mcp", AISTACK_DIR).tamer_endpoints()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"cannot load the Lumo helpers ({type(e).__name__}: {e}); nothing was sent"}
    prompt = PROMPT.format(
        today=time.strftime("%Y-%m-%d"),
        question=redact(question[:QUESTION_MAX]),
        context=("\nWHAT THE ASSISTANT ALREADY KNOWS:\n" + redact(context[:QUESTION_MAX])) if context else "",
    )
    errors = []
    for base, key in endpoints:
        messages = [{"role": "user", "content": prompt}]
        try:
            reply = ask(base, key, messages)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{base}: {type(e).__name__}: {e}")
            if "timed out" in str(e).lower():
                break  # a slow Lumo is slow on every endpoint; do not wait for each one
            continue
        retried = False
        if from_memory(reply):
            # Lumo decides per request whether to search, and sometimes answers from training data. One retry that
            # insists on web_search; its answer replaces the first one.
            retried = True
            try:
                reply = ask(base, key, messages + [{"role": "assistant", "content": reply},
                                                   {"role": "user", "content": RETRY}])
            except Exception:  # noqa: BLE001
                pass  # keep the first answer
        if len(reply) > REPLY_MAX:
            reply = reply[:REPLY_MAX] + "\n[reply cut at LUMO_MCP_REPLY_CHARS]"
        out = {"ok": True, "via": base, "answer": reply, "retried": retried}
        if from_memory(reply):
            out["warning"] = "Lumo did not answer from a web search; check the official source with WebFetch"
        return out
    return {
        "ok": False,
        "error": "; ".join(errors) or "no Lumo (lumo-tamer) answered",
        "hint": "Lumo is unreachable (run lumoreauth, or check lumo-tamer). WebFetch still reads an exact URL.",
    }


TOOLS = {
    "lumo_search": (
        lumo_search,
        "Search the web through Lumo and get a sourced answer (one call). Use instead of WebSearch.",
        {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "One specific question, with product names and versions."},
                "context": {"type": "string", "description": "Optional: what you already know or tried, so Lumo does not repeat it."},
            },
            "required": ["question"],
        },
    ),
}


def handle(req):
    m = req.get("method")
    if m == "initialize":
        return {
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "lumo", "version": "0.1.0"},
            "instructions": INSTRUCTIONS,
        }
    if m == "ping":
        return {}
    if m == "tools/list":
        # anthropic/alwaysLoad: Claude Code loads the tool upfront instead of behind ToolSearch (one turn fewer)
        return {"tools": [{"name": n, "description": d, "inputSchema": s, "_meta": {"anthropic/alwaysLoad": True}}
                          for n, (_, d, s) in TOOLS.items()]}
    if m == "tools/call":
        p = req.get("params", {})
        tool = TOOLS.get(p.get("name"))
        if not tool:
            return {"content": [{"type": "text", "text": f"unknown tool {p.get('name')}"}], "isError": True}
        out = tool[0](p.get("arguments") or {})
        text = (out["answer"] + f"\n\n(via {out['via']}" + (", after one retry" if out.get("retried") else "") + ")"
                + (f"\nWARNING: {out['warning']}" if out.get("warning") else "")) if out.get("ok") else json.dumps(out, indent=1)
        return {"content": [{"type": "text", "text": text}], "isError": not out.get("ok")}
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            continue
        if "id" not in req:
            continue
        try:
            res = handle(req)
            msg = (
                {"jsonrpc": "2.0", "id": req["id"], "result": res}
                if res is not None
                else {"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32601, "message": "method not found"}}
            )
        except Exception as e:  # noqa: BLE001
            msg = {"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32603, "message": str(e)}}
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
