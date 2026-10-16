// Advisor mode for OpenCode: the same policy as Claude Code's advisor mode (.config/aistack/advisor_hook.py).
//
// Sessions start in the `advisor` agent (default_agent in opencode.json). In that agent, and in every subagent it
// starts, reads go through and changes are refused: each tool call is translated to the Claude Code form and judged
// by advisor_hook.py, so both tools share one list of read-only commands, ssh/SSM rules and MCP rules. A refusal is
// thrown as an error, and its text tells the model to hand the user the command or diff with an explanation.
// Read-only bash runs without a permission prompt (permission.ask). The advisor answer format is added to the system
// prompt (advisor-prompt.md).
//
// Off for a session: switch to the `build` agent (Tab). Scripted `opencode run` calls pass `--agent build`.
// Fails closed: a session it knows nothing about counts as advisor, and a broken check refuses the call.

import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const HOOK =
  process.env.ADVISOR_HOOK ||
  path.join(os.homedir(), ".config", "aistack", "advisor_hook.py");
const ADVISOR_AGENT = "advisor";

let PROMPT = "";
try {
  PROMPT = readFileSync(path.join(HERE, "..", "advisor-prompt.md"), "utf8");
} catch {
  PROMPT =
    "Advisor mode: investigate freely, but the user makes every change. Give the exact command or diff, explain it, and let the user run it.";
}

// OpenCode tool -> [Claude Code tool, argument renames]
const TOOL_MAP = {
  read: ["Read", { filePath: "file_path" }],
  grep: ["Grep", {}],
  glob: ["Glob", {}],
  list: ["LS", {}],
  lsp: ["LSP", {}],
  webfetch: ["WebFetch", {}],
  websearch: ["WebSearch", {}],
  todoread: ["TodoWrite", {}],
  todowrite: ["TodoWrite", {}],
  task: ["Agent", {}],
  skill: ["Skill", {}],
  question: ["AskUserQuestion", {}],
  bash: ["Bash", {}],
  edit: ["Edit", { filePath: "file_path" }],
  write: ["Write", { filePath: "file_path" }],
  patch: ["Edit", { filePath: "file_path" }],
  apply_patch: ["Edit", { filePath: "file_path" }],
  multiedit: ["Edit", { filePath: "file_path" }],
};

function toClaude(tool, args, mcpServers) {
  args = args || {};
  if (tool === "mcp-lazy_mcp_search_tools")
    return { tool_name: "mcp__mcp-lazy__search_tools", tool_input: args };
  if (tool === "mcp-lazy_mcp_execute_tool") {
    // judge the proxied tool, not the proxy
    return {
      tool_name: `mcp__${args.server_name}__${args.tool_name}`,
      tool_input: args.arguments || {},
    };
  }
  if (TOOL_MAP[tool]) {
    const [name, renames] = TOOL_MAP[tool];
    const input = {};
    for (const [k, v] of Object.entries(args)) input[renames[k] || k] = v;
    return { tool_name: name, tool_input: input };
  }
  // MCP tools are <server>_<tool>; server names can contain "_" or "-", so match the configured names, longest first
  const server = [...mcpServers]
    .sort((a, b) => b.length - a.length)
    .find((s) => tool.startsWith(s + "_"));
  if (server)
    return {
      tool_name: `mcp__${server}__${tool.slice(server.length + 1)}`,
      tool_input: args,
    };
  return { tool_name: tool, tool_input: args }; // unknown: advisor_hook.py refuses it
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

// OpenCode calls every export of a plugin file as a plugin, so the helpers above stay unexported.
export default async () => {
  const mode = new Map(); // sessionID -> "advisor" | "off"
  const inherited = new Set(); // subagent sessions: their mode comes from the parent
  let mcpServers = [];

  const isAdvisor = (sessionID) =>
    (mode.get(sessionID) ?? "advisor") === "advisor";

  const check = (tool, args, sessionID) => {
    const ev = {
      hook_event_name: "PreToolUse",
      ...toClaude(tool, args, mcpServers),
      opencode_session: sessionID,
    };
    return judge(ev);
  };

  return {
    config: async (cfg) => {
      mcpServers = Object.keys(cfg?.mcp || {});
    },
    event: async ({ event }) => {
      if (event?.type !== "session.created") return;
      const info = event.properties?.info;
      if (info?.id && info.parentID) {
        mode.set(info.id, isAdvisor(info.parentID) ? "advisor" : "off");
        inherited.add(info.id);
      }
    },
    "chat.message": async (input, output) => {
      const sid = input?.sessionID;
      if (!sid || inherited.has(sid)) return;
      const agent = input.agent || output?.message?.agent;
      if (agent) mode.set(sid, agent === ADVISOR_AGENT ? "advisor" : "off");
    },
    "experimental.chat.system.transform": async (input, output) => {
      if (
        input?.sessionID &&
        isAdvisor(input.sessionID) &&
        Array.isArray(output?.system)
      )
        output.system.push(PROMPT);
    },
    "tool.execute.before": async (input, output) => {
      if (!isAdvisor(input?.sessionID)) return;
      const { decision, reason } = check(
        input.tool,
        output?.args,
        input.sessionID,
      );
      if (decision === "deny") throw new Error(reason);
    },
    "permission.ask": async (input, output) => {
      // read-only bash runs without a prompt; anything else keeps the normal prompt
      if (!isAdvisor(input?.sessionID) || input?.type !== "bash") return;
      const pattern = Array.isArray(input.pattern)
        ? input.pattern.join(" ")
        : input.pattern;
      const command = input.metadata?.command || pattern;
      if (
        typeof command === "string" &&
        check("bash", { command }, input.sessionID).decision === "allow"
      ) {
        output.status = "allow";
      }
    },
  };
};
