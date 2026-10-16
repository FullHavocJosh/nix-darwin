// Advisor mode for OpenCode: the same policy as Claude Code's advisor mode (.config/aistack/advisor_hook.py).
// OpenCode V2 plugin format: a default export { id, setup(ctx) } that registers hooks on ctx.
//
// Sessions start in the `advisor` agent (default_agent in opencode.json). In that agent, and in every subagent an
// advisor session starts, reads go through and changes are refused: each tool call is translated to the Claude Code
// form and judged by advisor_hook.py, so both tools share one list of read-only commands, ssh/SSM rules and MCP
// rules. A refusal is thrown as the tool error, and its text tells the model to hand the user the command or diff
// with an explanation. Read-only shell commands skip the permission prompt (permission "evaluate"), and the advisor
// answer format (advisor-prompt.md) is added to the system prompt (session "context").
//
// Off for a session: switch to the `build` agent (Tab). Scripted `opencode run` calls pass `--agent build`.
// Fails closed: a subagent whose parent is unknown counts as advisor, and a broken check refuses the call.
// ADVISOR_DEBUG=1 logs every tool call it sees to ~/.cache/advisor/opencode-tools.jsonl.

import { spawnSync } from "node:child_process";
import { appendFileSync, mkdirSync, readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const HOOK =
  process.env.ADVISOR_HOOK ||
  path.join(os.homedir(), ".config", "aistack", "advisor_hook.py");
const CONFIG =
  process.env.ADVISOR_OPENCODE_CONFIG || path.join(HERE, "..", "opencode.json");
const DEBUG_LOG = path.join(
  process.env.CLAUDE_ADVISOR_STATE ||
    path.join(os.homedir(), ".cache", "advisor"),
  "opencode-tools.jsonl",
);
const ADVISOR = "advisor";
const PRIMARY = new Set(["build", "plan"]); // primary agents that may change things

function readPrompt() {
  try {
    return readFileSync(path.join(HERE, "..", "advisor-prompt.md"), "utf8");
  } catch {
    return "Advisor mode: investigate freely, but the user makes every change. Give the exact command or diff, explain it, and let the user run it.";
  }
}

function mcpServers() {
  try {
    return Object.keys(JSON.parse(readFileSync(CONFIG, "utf8")).mcp || {});
  } catch {
    return [];
  }
}

// OpenCode tool (V2 names first, V1 names kept) -> [Claude Code tool, argument renames]
const FILE = { filePath: "file_path", path: "file_path" };
const TOOL_MAP = {
  shell: ["Bash", {}],
  bash: ["Bash", {}],
  read: ["Read", FILE],
  grep: ["Grep", {}],
  glob: ["Glob", {}],
  list: ["LS", {}],
  lsp: ["LSP", {}],
  webfetch: ["WebFetch", {}],
  websearch: ["WebSearch", {}],
  todoread: ["TodoWrite", {}],
  todowrite: ["TodoWrite", {}],
  subagent: ["Agent", {}],
  task: ["Agent", {}],
  skill: ["Skill", {}],
  question: ["AskUserQuestion", {}],
  edit: ["Edit", FILE],
  write: ["Write", FILE],
  patch: ["Edit", FILE],
  apply_patch: ["Edit", FILE],
  multiedit: ["Edit", FILE],
};

function toClaude(tool, input, servers) {
  input = input && typeof input === "object" ? input : {};
  if (tool === "mcp-lazy_mcp_search_tools")
    return { tool_name: "mcp__mcp-lazy__search_tools", tool_input: input };
  if (tool === "mcp-lazy_mcp_execute_tool") {
    // judge the proxied tool, not the proxy
    return {
      tool_name: `mcp__${input.server_name}__${input.tool_name}`,
      tool_input: input.arguments || {},
    };
  }
  if (TOOL_MAP[tool]) {
    const [name, renames] = TOOL_MAP[tool];
    const out = {};
    for (const [k, v] of Object.entries(input)) out[renames[k] || k] = v;
    return { tool_name: name, tool_input: out };
  }
  // MCP tools are <server>_<tool>; server names can contain "_" or "-", so match the configured names, longest first
  const server = [...servers]
    .sort((a, b) => b.length - a.length)
    .find((s) => tool.startsWith(s + "_"));
  if (server)
    return {
      tool_name: `mcp__${server}__${tool.slice(server.length + 1)}`,
      tool_input: input,
    };
  return { tool_name: tool, tool_input: input }; // unknown: advisor_hook.py refuses it
}

function judge(event) {
  const p = spawnSync("python3", [HOOK], {
    input: JSON.stringify(event),
    encoding: "utf8",
    timeout: 10000,
  });
  if (p.error || p.status !== 0) {
    return {
      decision: "deny",
      reason: `advisor check failed (${p.error?.message || p.stderr || p.status}); switch to the build agent to get past it`,
    };
  }
  const out = (p.stdout || "").trim();
  if (!out) return { decision: null, reason: "" };
  try {
    const h = JSON.parse(out).hookSpecificOutput || {};
    return {
      decision: h.permissionDecision || null,
      reason: h.permissionDecisionReason || "",
    };
  } catch {
    return {
      decision: "deny",
      reason: "advisor check returned something unreadable",
    };
  }
}

function debug(record) {
  if (process.env.ADVISOR_DEBUG !== "1") return;
  try {
    mkdirSync(path.dirname(DEBUG_LOG), { recursive: true });
    appendFileSync(
      DEBUG_LOG,
      JSON.stringify({ ts: Date.now(), ...record }) + "\n",
    );
  } catch {}
}

export default {
  id: "fullhavoc.advisor-guard",
  async setup(ctx) {
    const PROMPT = readPrompt();
    const servers = mcpServers();
    const parent = new Map(); // child session -> parent session, from session.created events
    const mode = new Map(); // session -> "advisor" | "off", from the agent a primary session runs

    const remember = (sessionID, agent) => {
      if (!sessionID || !agent) return;
      if (agent === ADVISOR) mode.set(sessionID, "advisor");
      else if (PRIMARY.has(agent)) mode.set(sessionID, "off");
    };
    const isAdvisor = (sessionID, agent) => {
      remember(sessionID, agent);
      if (mode.has(sessionID)) return mode.get(sessionID) === "advisor";
      // a subagent: follow its parent; unknown parent fails closed
      let s = sessionID;
      for (let i = 0; i < 20 && parent.has(s); i++) {
        s = parent.get(s);
        if (mode.has(s)) return mode.get(s) === "advisor";
      }
      return true;
    };
    const check = (tool, input) =>
      judge({
        hook_event_name: "PreToolUse",
        ...toClaude(tool, input, servers),
      });

    const controller = new AbortController();
    if (ctx.event?.subscribe) {
      void (async () => {
        try {
          for await (const ev of ctx.event.subscribe({
            signal: controller.signal,
          })) {
            const info = ev?.properties?.info ?? ev?.data?.info ?? ev?.info;
            if (info?.id && info.parentID) parent.set(info.id, info.parentID);
            if (info?.id && info.agent) remember(info.id, info.agent);
          }
        } catch {}
      })();
    }

    await ctx.tool.hook("execute.before", (event) => {
      const advisor = isAdvisor(event.sessionID, event.agent);
      debug({
        tool: event.tool,
        agent: event.agent,
        sessionID: event.sessionID,
        advisor,
        input: event.input,
      });
      // Code Mode: every tool its code calls comes through this hook again under its own name (seen live in 2.0.29),
      // so the code itself is let through and each call it makes is judged
      if (!advisor || event.tool === "execute") return;
      const { decision, reason } = check(event.tool, event.input);
      if (decision === "deny") throw new Error(reason);
    });

    await ctx.permission.hook("evaluate", (event) => {
      // read-only shell commands run without a prompt; anything else keeps its normal decision
      if (
        event.effect !== "ask" ||
        !["shell", "bash"].includes(event.action) ||
        !isAdvisor(event.sessionID, event.agent)
      )
        return;
      const command =
        typeof event.metadata?.command === "string"
          ? event.metadata.command
          : (event.resources || []).join(" ");
      if (command && check("shell", { command }).decision === "allow")
        event.effect = "allow";
    });

    await ctx.session.hook("context", (event) => {
      if (
        isAdvisor(event.sessionID, event.agent) &&
        Array.isArray(event.system)
      )
        event.system.push({ type: "text", text: PROMPT });
    });

    return () => controller.abort();
  },
};
