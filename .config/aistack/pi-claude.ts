// ai: pi as the front end, Claude Code as the brain.
//
// Every message typed into pi goes to `claude -p` (Claude Code, on the user's own login, with their CLAUDE.md, MCP
// servers, hooks and advisor mode) and Claude's replies and tool activity are shown in pi. pi's own model never runs:
// `ai` starts pi with --no-tools and this extension handles every message.
//
//   - One Claude Code session per pi session: the first message starts it with --session-id <uuid>, later ones
//     --resume it. pi writes no session file when its own model never answers, so the last Claude session of each
//     directory is kept in ~/.ai/ai/claude-sessions.json, and `ai -c` continues it.
//   - Commands the user runs with pi's `!cmd` are passed to Claude, with their output, ahead of the next message.
//   - /advisor on|off|status switches Claude Code's advisor mode for this conversation (advisor_hook.py keys its
//     switch by the Claude session id, which pi's own shell does not have).
//   - AI_CLAUDE_MODEL (default sonnet) picks the model; AI_CLAUDE_ARGS adds claude flags.
//
// Loaded only by `ai` (pi -e ...), never by plain pi, ainfo or aidev.

import { spawn, spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const MODEL = process.env.AI_CLAUDE_MODEL || "sonnet";
const EXTRA = (process.env.AI_CLAUDE_ARGS || "").split(/\s+/).filter(Boolean);
const CLAUDE = process.env.AI_CLAUDE_BIN || "claude";
const ADVISOR = path.join(homedir(), ".config", "aistack", "advisor_hook.py");
const STATE = path.join(
  process.env.PI_CODING_AGENT_DIR ||
    path.join(
      (process.env.AI_HOME || path.join(homedir(), ".ai")).replace(
        /^~(?=$|\/)/,
        homedir(),
      ),
      "ai",
    ),
  "claude-sessions.json",
);
const CONTINUE = process.argv.some((a) => a === "-c" || a === "--continue");

function readState(): Record<string, { id: string; ts: number }> {
  try {
    return JSON.parse(readFileSync(STATE, "utf8"));
  } catch {
    return {};
  }
}

function remember(cwd: string, id: string) {
  const state = readState();
  state[cwd] = { id, ts: Date.now() };
  try {
    mkdirSync(path.dirname(STATE), { recursive: true });
    writeFileSync(STATE, JSON.stringify(state, null, 1));
  } catch {}
}
const APPEND =
  "The user is talking to you through pi, a terminal front end. They run shell commands themselves by typing " +
  "`!<command>` in pi; commands they ran since your last reply are listed at the start of their message, with output.";

type Block = {
  type: string;
  text?: string;
  name?: string;
  input?: Record<string, unknown>;
};

// one short line per tool call, like Claude Code's own transcript
function brief(name: string, input: Record<string, unknown> = {}): string {
  const arg =
    input.command ??
    input.file_path ??
    input.path ??
    input.pattern ??
    input.url ??
    input.query ??
    input.question ??
    "";
  const s = String(arg).replace(/\s+/g, " ");
  return `${name}${s ? `(${s.length > 100 ? s.slice(0, 100) + "…" : s})` : ""}`;
}

export default function (pi: ExtensionAPI) {
  let session: string | undefined; // Claude Code session id
  let started = false; // whether that session exists on Claude's side yet
  let lastTurn = 0; // timestamp of the last message sent to Claude

  pi.on("session_start", async (_event, ctx) => {
    session = undefined;
    started = false;
    lastTurn = 0;
    for (const entry of ctx.sessionManager.getBranch() as any[]) {
      if (
        entry.type === "custom" &&
        entry.customType === "claude-session" &&
        entry.data?.id
      ) {
        session = entry.data.id;
        started = true;
      }
      if (entry.type === "custom" && entry.customType === "claude-turn")
        lastTurn = entry.data?.ts ?? lastTurn;
    }
    const last = readState()[ctx.sessionManager.getCwd()];
    if (!session && CONTINUE && last?.id) {
      session = last.id;
      started = true;
    }
  });

  // `!cmd` runs since the last turn, so Claude sees what the user did
  function userCommands(ctx: any): string {
    const out: string[] = [];
    for (const entry of ctx.sessionManager.getBranch() as any[]) {
      const m = entry.type === "message" ? entry.message : undefined;
      if (
        m?.role !== "bashExecution" ||
        m.excludeFromContext ||
        (m.timestamp ?? 0) <= lastTurn
      )
        continue;
      const body = String(m.output ?? "").slice(-6000);
      out.push(
        `$ ${m.command}\n${body}${m.exitCode ? `\n(exit ${m.exitCode})` : ""}`,
      );
    }
    return out.length
      ? `Commands I ran since your last reply:\n\n${out.join("\n\n")}\n\n---\n\n`
      : "";
  }

  pi.registerCommand("advisor", {
    description:
      "Claude Code advisor mode for this conversation: on, off or status",
    handler: async (args, ctx) => {
      const what = args.trim() || "status";
      if (!session) {
        ctx.ui.notify(
          "No Claude session yet: send a message first.",
          "warning",
        );
        return;
      }
      const r = spawnSync("python3", [ADVISOR, what], {
        env: { ...process.env, CLAUDE_CODE_SESSION_ID: session },
        encoding: "utf8",
      });
      ctx.ui.notify(
        (r.stdout || r.stderr || "").trim() || `advisor exited ${r.status}`,
        r.status ? "error" : "info",
      );
    },
  });

  pi.on("input", async (event, ctx) => {
    if (event.source === "extension") return { action: "continue" };
    const text = event.text.trim();
    if (!text || text.startsWith("/") || text.startsWith("!"))
      return { action: "continue" };

    if (!session) {
      session = randomUUID();
      pi.appendEntry("claude-session", { id: session });
    }
    const prompt = userCommands(ctx) + text;
    const args = [
      "-p",
      "--output-format",
      "stream-json",
      "--verbose",
      "--model",
      MODEL,
      ...(started ? ["--resume", session] : ["--session-id", session]),
      "--append-system-prompt",
      APPEND,
      ...EXTRA,
    ];
    lastTurn = Date.now();
    pi.appendEntry("claude-turn", { ts: lastTurn });
    await pi.sendMessage({
      customType: "you",
      content: `> ${text}`,
      display: true,
    });

    const env = { ...process.env };
    delete env.CLAUDECODE; // ai may be started from inside a Claude Code shell
    const child = spawn(CLAUDE, args, {
      cwd: ctx.sessionManager.getCwd(),
      env,
      stdio: ["pipe", "pipe", "pipe"],
    });
    const abort = () => child.kill("SIGTERM");
    ctx.signal?.addEventListener("abort", abort, { once: true });
    child.stdin.end(prompt);

    let buffer = "";
    let stderr = "";
    let result: any;
    const shown: Promise<unknown>[] = [];
    ctx.ui.setStatus("claude", `Claude Code (${MODEL}) is working…`);
    child.stderr.on("data", (d) => (stderr += d.toString()));
    child.stdout.on("data", (d) => {
      buffer += d.toString();
      let nl: number;
      while ((nl = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, nl).trim();
        buffer = buffer.slice(nl + 1);
        if (!line) continue;
        let ev: any;
        try {
          ev = JSON.parse(line);
        } catch {
          continue;
        }
        if (ev.type === "assistant") {
          for (const b of (ev.message?.content ?? []) as Block[]) {
            if (b.type === "text" && b.text?.trim()) {
              if (ctx.mode === "print") console.log(b.text);
              shown.push(
                pi.sendMessage({
                  customType: "claude",
                  content: b.text,
                  display: true,
                }),
              );
            } else if (b.type === "tool_use") {
              const line = brief(b.name ?? "?", b.input);
              ctx.ui.setStatus("claude", `Claude: ${line}`);
              shown.push(
                pi.sendMessage({
                  customType: "claude-tool",
                  content: `⏺ ${line}`,
                  display: true,
                }),
              );
            }
          }
        } else if (ev.type === "result") {
          result = ev;
        }
      }
    });
    const code: number = await new Promise((resolve) =>
      child.on("close", (c) => resolve(c ?? 1)),
    );
    ctx.signal?.removeEventListener("abort", abort);
    await Promise.all(shown);
    ctx.ui.setStatus("claude", undefined);

    if (result && !result.is_error) {
      started = true;
      remember(ctx.sessionManager.getCwd(), session);
      const cost = Number(result.total_cost_usd || 0);
      ctx.ui.setStatus(
        "claude-cost",
        `Claude ${MODEL} $${cost.toFixed(3)} last turn`,
      );
    } else if (ctx.signal?.aborted) {
      ctx.ui.notify("Claude Code stopped.", "warning");
    } else {
      const why = String(result?.result || stderr || `claude exited ${code}`)
        .trim()
        .slice(0, 600);
      // a resume of a session Claude does not have (deleted, other machine) starts over next time
      if (started && /no conversation found|session.*not found/i.test(why)) {
        session = randomUUID();
        started = false;
        pi.appendEntry("claude-session", { id: session });
      }
      ctx.ui.notify(`Claude Code failed: ${why}`, "error");
      if (ctx.mode === "print") console.error(why);
    }
    return { action: "handled" };
  });
}
