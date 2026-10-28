// Worktree guard: blocks pi's edit, write and bash tools from changing a repository's main checkout.
//
// Ported from the Claude Code PreToolUse hook (~/mcp-stack-fullhavoc/hooks/pretooluse_gate.py) and the OpenCode
// plugin (.config/opencode/plugins/git-workflow-guard.js), with the same rules:
//   - edit/write: block when the file's repository is at its main checkout (--git-dir == --git-common-dir).
//   - bash: block file-writing forms (sed -i, tee, redirects, git apply, patch) run from a main checkout.
// Edits fail closed on a git error; bash fails open, since a command's cwd is a weaker signal than a file path.
// Loaded from ~/.pi/agent/extensions by plain pi, and with `-e` by coder_pi.py for aidev builders.
// PI_WORKTREE_GUARD=0 turns it off.

import { execFile } from "node:child_process";
import path from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const BASH_WRITE_RE =
  /\bsed\s+(?:-[A-Za-z]*\s+)*-[A-Za-z]*i|\bperl\s+-[A-Za-z]*i|\btee\b|\bgit\s+apply\b|\bpatch\b|(?<![>&\d])\d?>>?\s*(?!&|\/dev\/null|\/tmp\/|\/private\/tmp\/)[^\s&|;]/;

function git(
  dir: string,
  args: string[],
): Promise<{ err: boolean; out: string; stderr: string }> {
  return new Promise((resolve) => {
    execFile(
      "git",
      ["-C", dir, ...args],
      { timeout: 5000 },
      (error, stdout, stderr) =>
        resolve({
          err: !!error,
          out: (stdout ?? "").trim(),
          stderr: stderr ?? "",
        }),
    );
  });
}

// "none" = not inside a git repo; "error" = git failed for another reason.
async function mainCheckout(dir: string): Promise<{
  state: "main" | "linked" | "none" | "error";
  root?: string;
  msg?: string;
}> {
  const top = await git(dir, ["rev-parse", "--show-toplevel"]);
  if (top.err) {
    return /not a git repository/i.test(top.stderr)
      ? { state: "none" }
      : { state: "error", msg: top.stderr };
  }
  const [gitDir, common] = await Promise.all([
    git(top.out, ["rev-parse", "--path-format=absolute", "--git-dir"]),
    git(top.out, ["rev-parse", "--path-format=absolute", "--git-common-dir"]),
  ]);
  if (gitDir.err || common.err)
    return { state: "error", msg: gitDir.stderr || common.stderr };
  return {
    state: gitDir.out === common.out ? "main" : "linked",
    root: top.out,
  };
}

export default function (pi: ExtensionAPI) {
  if (process.env.PI_WORKTREE_GUARD === "0") return;

  pi.on("tool_call", async (event, ctx) => {
    const input = event.input as Record<string, unknown>;

    if (event.toolName === "edit" || event.toolName === "write") {
      const filePath = typeof input.path === "string" ? input.path : "";
      if (!filePath) return;
      const dir = path.dirname(path.resolve(ctx.cwd, filePath));
      const res = await mainCheckout(dir);
      if (res.state === "none" || res.state === "linked") return;
      if (res.state === "error") {
        return {
          block: true,
          reason: `[worktree-guard] git failed in ${dir}: ${res.msg}. Refusing to edit until this is resolved.`,
        };
      }
      return {
        block: true,
        reason:
          `[worktree-guard] Editing directly in the primary repo checkout (${res.root}) is not allowed. ` +
          `Run 'gpr' to create a worktree for this work, then edit there.`,
      };
    }

    if (event.toolName === "bash") {
      const command = typeof input.command === "string" ? input.command : "";
      if (!BASH_WRITE_RE.test(command)) return;
      const res = await mainCheckout(ctx.cwd);
      if (res.state !== "main") return;
      return {
        block: true,
        reason:
          `[worktree-guard] File-writing command in the primary repo checkout (${res.root}) is not allowed. ` +
          `Run 'gpr' to create a worktree for this work, then run it there.`,
      };
    }
  });
}
