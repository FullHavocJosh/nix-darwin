// Tests for .config/opencode/plugins/advisor-guard.js (advisor mode for OpenCode). Drives the plugin's hooks with
// fake OpenCode events against the real advisor_hook.py. Run: node .config/aistack/tests/test_advisor_guard.mjs
import { mkdtempSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "..", "..", "..");
const PLUGIN = pathToFileURL(path.join(REPO, ".config/opencode/plugins/advisor-guard.js")).href;
const T = mkdtempSync(path.join(os.tmpdir(), "advisor-guard-"));
writeFileSync(path.join(T, "aws-config"), "[profile ops-ro]\nsso_role_name = OpsReadOnly\n");
Object.assign(process.env, {
  ADVISOR_HOOK: path.join(REPO, ".config/aistack/advisor_hook.py"),
  CLAUDE_ADVISOR_STATE: path.join(T, "state"),
  AWS_CONFIG_FILE: path.join(T, "aws-config"),
});
delete process.env.CLAUDE_ADVISOR;
const FAILS = [];

function check(name, cond, extra = "") {
  console.log((cond ? "  PASS " : "  FAIL ") + name + (!cond && extra ? `  [${extra}]` : ""));
  if (!cond) FAILS.push(name);
}

async function load(tag) {
  const mod = await import(`${PLUGIN}?${tag}`);
  const hooks = await mod.default({});
  await hooks.config({ mcp: { lumo: {}, "local-edit": {}, "mcp-lazy": {}, github: {} } });
  return hooks;
}

const h = await load("main");

async function refused(sessionID, tool, args) {
  try {
    await h["tool.execute.before"]({ tool, sessionID, callID: "c" }, { args });
    return "";
  } catch (e) {
    return e.message || "refused";
  }
}

await h["chat.message"]({ sessionID: "adv", agent: "advisor" }, { message: {}, parts: [] });
await h["chat.message"]({ sessionID: "bld", agent: "build" }, { message: {}, parts: [] });

console.log("advisor agent");
check("read-only bash goes through", (await refused("adv", "bash", { command: "git status" })) === "");
const why = await refused("adv", "bash", { command: "rm -rf build" });
check("a changing command is refused with the advisor instructions", why.includes("Advisor mode") && why.includes("! <command>"), why);
check("ssh with a changing remote command is refused", (await refused("adv", "bash", { command: "ssh web1 'systemctl restart nginx'" })) !== "");
check("edit and write are refused", (await refused("adv", "edit", { filePath: "/x/a.py" })) !== "" && (await refused("adv", "write", { filePath: "/x/b.py" })) !== "");
check("read goes through, credential files do not", (await refused("adv", "read", { filePath: "/etc/hosts" })) === ""
  && (await refused("adv", "read", { filePath: path.join(os.homedir(), ".ssh/id_ed25519") })) !== "");
check("read MCP tools go through (server names with - too)", (await refused("adv", "lumo_lumo_search", { question: "q" })) === "");
check("write MCP tools are refused", (await refused("adv", "local-edit_local_edit", {})) !== "");
check("mcp-lazy: search goes through", (await refused("adv", "mcp-lazy_mcp_search_tools", { query: "pr" })) === "");
check("mcp-lazy: the proxied tool is judged, a read goes through",
  (await refused("adv", "mcp-lazy_mcp_execute_tool", { server_name: "github", tool_name: "github_pr_list", arguments: {} })) === "");
check("mcp-lazy: a proxied write is refused",
  (await refused("adv", "mcp-lazy_mcp_execute_tool", { server_name: "github", tool_name: "github_pr_create", arguments: {} })) !== "");
check("an unknown tool is refused", (await refused("adv", "mystery_tool", {})) !== "");

console.log("other agents and sessions");
check("the build agent is not checked", (await refused("bld", "bash", { command: "rm -rf build" })) === "");
check("a session it has not seen counts as advisor (fails closed)", (await refused("new", "bash", { command: "rm -rf build" })) !== "");
await h.event({ event: { type: "session.created", properties: { info: { id: "sub-adv", parentID: "adv" } } } });
await h["chat.message"]({ sessionID: "sub-adv", agent: "general" }, { message: {}, parts: [] });
check("a subagent of an advisor session stays advisor", (await refused("sub-adv", "bash", { command: "rm x" })) !== "");
await h.event({ event: { type: "session.created", properties: { info: { id: "sub-bld", parentID: "bld" } } } });
check("a subagent of a build session is not checked", (await refused("sub-bld", "bash", { command: "rm x" })) === "");
await h["chat.message"]({ sessionID: "adv2", agent: "build" }, { message: {}, parts: [] });
await h["chat.message"]({ sessionID: "adv2", agent: "advisor" }, { message: {}, parts: [] });
check("switching back to advisor turns it on again", (await refused("adv2", "bash", { command: "rm x" })) !== "");

console.log("prompt and permissions");
let out = { system: [] };
await h["experimental.chat.system.transform"]({ sessionID: "adv", model: {} }, out);
check("the advisor answer format is added for advisor sessions", out.system.length === 1 && out.system[0].includes("unified diff"), out.system);
out = { system: [] };
await h["experimental.chat.system.transform"]({ sessionID: "bld", model: {} }, out);
check("and not for build sessions", out.system.length === 0);
let st = { status: "ask" };
await h["permission.ask"]({ type: "bash", pattern: "git log --oneline -3", sessionID: "adv", metadata: {} }, st);
check("read-only bash needs no permission prompt", st.status === "allow");
st = { status: "ask" };
await h["permission.ask"]({ type: "bash", pattern: "rm x", sessionID: "adv", metadata: {} }, st);
check("anything else keeps the prompt", st.status === "ask");

console.log("failure");
process.env.ADVISOR_HOOK = path.join(T, "missing.py");
const broken = await load("broken");
await broken["chat.message"]({ sessionID: "adv", agent: "advisor" }, { message: {}, parts: [] });
let msg = "";
try {
  await broken["tool.execute.before"]({ tool: "bash", sessionID: "adv", callID: "c" }, { args: { command: "ls" } });
} catch (e) {
  msg = e.message;
}
check("a broken check refuses the call", msg.includes("advisor check failed"), msg);

console.log(FAILS.length ? `\nFAILED: ${FAILS}` : "\nALL PASSED");
process.exit(FAILS.length ? 1 : 0);
