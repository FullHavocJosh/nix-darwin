// Tests for the OpenCode V2 plugins in .config/opencode/plugins: advisor-guard.js (advisor mode, against the real
// advisor_hook.py) and git-workflow-guard.js. A fake ctx records the hooks each plugin registers in setup(), and the
// tests call them with OpenCode-shaped events. Run: node .config/aistack/tests/test_advisor_guard.mjs
import { mkdtempSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "..", "..", "..");
const PLUGINS = path.join(REPO, ".config/opencode/plugins");
const T = mkdtempSync(path.join(os.tmpdir(), "advisor-guard-"));
writeFileSync(path.join(T, "aws-config"), "[profile ops-ro]\nsso_role_name = OpsReadOnly\n");
writeFileSync(path.join(T, "opencode.json"), JSON.stringify({ mcp: { lumo: {}, "local-edit": {}, "mcp-lazy": {}, github: {}, "mcp-stack-fullhavoc": {} } }));
Object.assign(process.env, {
  ADVISOR_HOOK: path.join(REPO, ".config/aistack/advisor_hook.py"),
  ADVISOR_OPENCODE_CONFIG: path.join(T, "opencode.json"),
  CLAUDE_ADVISOR_STATE: path.join(T, "state"),
  AWS_CONFIG_FILE: path.join(T, "aws-config"),
});
delete process.env.CLAUDE_ADVISOR;
const FAILS = [];

function check(name, cond, extra = "") {
  console.log((cond ? "  PASS " : "  FAIL ") + name + (!cond && extra ? `  [${extra}]` : ""));
  if (!cond) FAILS.push(name);
}

// a fake V2 PluginContext: records hooks; the event stream replays `events`
async function load(file, tag, events = []) {
  const mod = await import(`${pathToFileURL(path.join(PLUGINS, file)).href}?${tag}`);
  const def = mod.default;
  const hooks = {};
  const reg = (domain) => ({ hook: async (name, cb) => { hooks[`${domain}.${name}`] = cb; return { dispose: async () => {} }; } });
  const ctx = {
    tool: reg("tool"),
    permission: reg("permission"),
    session: reg("session"),
    shell: reg("shell"),
    event: { subscribe: async function* () { for (const e of events) yield e; } },
  };
  const cleanup = await def.setup(ctx);
  await new Promise((r) => setTimeout(r, 20)); // let the event stream drain
  return { def, hooks, cleanup };
}

const created = (id, parentID) => ({ type: "session.created", properties: { info: { id, parentID } } });
const { def, hooks: h, cleanup } = await load("advisor-guard.js", "main", [created("sub-adv", "adv"), created("sub-bld", "bld")]);

async function refused(sessionID, agent, tool, input) {
  try {
    await h["tool.execute.before"]({ tool, sessionID, agent, messageID: "m", id: "c", input });
    return "";
  } catch (e) {
    return e.message || "refused";
  }
}

console.log("plugin format");
check("V2 default export: an id and a setup function", typeof def.id === "string" && def.id && typeof def.setup === "function");
check("it registers execute.before, permission evaluate and session context",
  ["tool.execute.before", "permission.evaluate", "session.context"].every((k) => typeof h[k] === "function"), Object.keys(h));
check("setup returns a cleanup function", typeof cleanup === "function");

console.log("advisor agent");
check("read-only shell goes through", (await refused("adv", "advisor", "shell", { command: "git status" })) === "");
const why = await refused("adv", "advisor", "shell", { command: "rm -rf build" });
check("a changing shell command is refused with the advisor instructions", why.includes("Advisor mode") && why.includes("! <command>"), why);
check("the V1 name bash is checked too", (await refused("adv", "advisor", "bash", { command: "rm -rf build" })) !== "");
check("ssh with a changing remote command is refused", (await refused("adv", "advisor", "shell", { command: "ssh web1 'systemctl restart nginx'" })) !== "");
check("edit, write and apply_patch are refused", (await refused("adv", "advisor", "edit", { filePath: "/x/a.py" })) !== ""
  && (await refused("adv", "advisor", "write", { filePath: "/x/b.py" })) !== "" && (await refused("adv", "advisor", "apply_patch", { patch: "x" })) !== "");
check("read goes through, credential files do not", (await refused("adv", "advisor", "read", { filePath: "/etc/hosts" })) === ""
  && (await refused("adv", "advisor", "read", { filePath: path.join(os.homedir(), ".ssh/id_ed25519") })) !== "");
check("read MCP tools go through (server names with - too)", (await refused("adv", "advisor", "lumo_lumo_search", { question: "q" })) === "");
check("write MCP tools are refused", (await refused("adv", "advisor", "local-edit_local_edit", {})) !== "");
check("mcp-lazy: the proxied tool is judged, a read goes through",
  (await refused("adv", "advisor", "mcp-lazy_mcp_execute_tool", { server_name: "github", tool_name: "github_pr_list", arguments: {} })) === "");
check("mcp-lazy: a proxied write is refused",
  (await refused("adv", "advisor", "mcp-lazy_mcp_execute_tool", { server_name: "github", tool_name: "github_pr_create", arguments: {} })) !== "");
check("Code Mode execute goes through (each tool it calls is judged on its own)", (await refused("adv", "advisor", "execute", { code: "return 1" })) === "");
check("MCP tools called from Code Mode are judged: a read goes through, a write is refused", (await refused("adv", "advisor", "mcp-stack-fullhavoc_validate_command", { command: "ls" })) === ""
  && (await refused("adv", "advisor", "github_github_pr_create", {})) !== "");
check("subagent starts go through", (await refused("adv", "advisor", "subagent", { prompt: "look" })) === "");

console.log("other agents and sessions");
check("the build agent is not checked", (await refused("bld", "build", "shell", { command: "rm -rf build" })) === "");
check("a subagent of an advisor session is checked", (await refused("sub-adv", "general", "shell", { command: "rm x" })) !== "");
check("a subagent of a build session is not checked", (await refused("sub-bld", "general", "shell", { command: "rm x" })) === "");
check("a subagent with an unknown parent counts as advisor (fails closed)", (await refused("orphan", "general", "shell", { command: "rm x" })) !== "");
await refused("adv2", "build", "shell", { command: "true" });
check("switching from build to advisor turns it on", (await refused("adv2", "advisor", "shell", { command: "rm x" })) !== "");

console.log("prompt and permissions");
let ev = { sessionID: "adv", agent: "advisor", system: [] };
await h["session.context"](ev);
check("the advisor answer format is added for advisor sessions", ev.system.length === 1 && ev.system[0].text.includes("unified diff"), JSON.stringify(ev.system));
ev = { sessionID: "bld", agent: "build", system: [] };
await h["session.context"](ev);
check("and not for build sessions", ev.system.length === 0);
let p = { sessionID: "adv", agent: "advisor", action: "shell", resources: ["git log --oneline -3"], effect: "ask" };
await h["permission.evaluate"](p);
check("read-only shell needs no permission prompt", p.effect === "allow");
p = { sessionID: "adv", agent: "advisor", action: "shell", resources: ["rm x"], effect: "ask" };
await h["permission.evaluate"](p);
check("anything else keeps the prompt", p.effect === "ask");

console.log("failure");
process.env.ADVISOR_HOOK = path.join(T, "missing.py");
const broken = (await load("advisor-guard.js", "broken")).hooks;
let msg = "";
try {
  await broken["tool.execute.before"]({ tool: "shell", sessionID: "a", agent: "advisor", input: { command: "ls" } });
} catch (e) {
  msg = e.message;
}
check("a broken check refuses the call", msg.includes("advisor check failed"), msg);

console.log("git-workflow-guard");
const g = await load("git-workflow-guard.js", "git");
check("V2 default export with an execute.before hook", typeof g.def.id === "string" && typeof g.hooks["tool.execute.before"] === "function");
let gm = "";
try {
  await g.hooks["tool.execute.before"]({ tool: "shell", sessionID: "s", agent: "build", input: { command: "gh pr merge 1" } });
} catch (e) {
  gm = e.message;
}
check("it still refuses gh pr merge, on the V2 shell tool", gm.includes("Merging PRs"), gm);
const n = await load("herdr-nvim-open-edited.js", "nvim");
check("herdr-nvim-open-edited: V2 default export", typeof n.def.id === "string" && typeof n.def.setup === "function");

console.log(FAILS.length ? `\nFAILED: ${FAILS}` : "\nALL PASSED");
process.exit(FAILS.length ? 1 : 0);
