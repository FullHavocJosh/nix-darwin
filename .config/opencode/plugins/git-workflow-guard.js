// Ported from the Claude Code PreToolUse hook at
// ~/mcp-context-guardian-fullhavoc/src/hook.ts + src/policies.ts.
//
// Claude Code enforces the gpr/gpa/gpc git-worktree-pr-workflow (see the
// git-worktree-pr-workflow skill) via a PreToolUse hook. opencode has no
// hook equivalent — this plugin closes that gap using opencode's
// tool.execute.before interception instead, with the same rules.

import { execFile } from "node:child_process";
import path from "node:path";

function run(cmd, args) {
  return new Promise((resolve) => {
    execFile(cmd, args, { timeout: 5000 }, (err, stdout, stderr) => {
      resolve({ err, stdout: stdout ?? "", stderr: stderr ?? "" });
    });
  });
}

// Mirrors hook.ts's findGitRoot: distinguishes "not in a git repo" (nothing
// to enforce) from any other git failure (fail closed, block the edit).
async function findGitRoot(filePath) {
  const dir = path.dirname(path.resolve(filePath));
  const { err, stdout, stderr } = await run("git", [
    "-C",
    dir,
    "rev-parse",
    "--show-toplevel",
  ]);
  if (err) {
    if (/not a git repository/i.test(stderr)) return { root: undefined };
    return {
      error: `'git rev-parse --show-toplevel' failed in ${dir}: ${stderr || err.message}`,
    };
  }
  return { root: stdout.trim() };
}

// Mirrors hook.ts's isMainWorktree: only the main checkout has --git-dir ===
// --git-common-dir; every linked worktree's --git-dir points into
// <main>/.git/worktrees/<name> instead.
async function isMainWorktree(repoDir) {
  const flags = ["--path-format=absolute"];
  const [gitDir, commonDir] = await Promise.all([
    run("git", ["-C", repoDir, "rev-parse", ...flags, "--git-dir"]),
    run("git", ["-C", repoDir, "rev-parse", ...flags, "--git-common-dir"]),
  ]);
  if (gitDir.err || commonDir.err) {
    const stderr = gitDir.stderr || commonDir.stderr || "";
    return {
      error: `'git rev-parse --git-dir/--git-common-dir' failed in ${repoDir}: ${stderr}`,
    };
  }
  return { isMain: gitDir.stdout.trim() === commonDir.stdout.trim() };
}

const GIT_MAIN_PUSH_RE =
  /git\s+push\s+.*\borigin\s+main\b|git\s+push\s+-u\s+origin\s+main\b|git\s+push\s+--set-upstream\s+origin\s+main\b/;

const FORBIDDEN_PATTERNS = [
  "rm -rf /",
  "rm -rf /*",
  "sudo rm",
  "sudo chmod",
  "sudo chown",
  "chmod 777",
  "> /dev/",
  "dd if=",
  "mkfs",
  "fdisk",
  "parted",
  ":(){ :|:& };:",
  "eval $(curl",
  "eval $(wget",
  'bash -c "$(curl',
  "git push origin main",
  "git push --set-upstream origin main",
  "git push -u origin main",
];

function invokes(command, fn) {
  return new RegExp(`\\b${fn}\\b`).test(command);
}

const GIT_COMMIT_RE = /\bgit\s+commit\b/;
const GH_PR_CREATE_RE = /\bgh\s+pr\s+create\b/;
const GH_PR_COMMENT_RE = /\bgh\s+pr\s+comment\b/;
const GH_PR_REVIEW_RE = /\bgh\s+pr\s+review\b/;
const GH_PR_MERGE_RE = /\bgh\s+pr\s+merge\b/;
const GIT_CHECKOUT_B_RE = /\bgit\s+checkout\s+-b\b/;
const GIT_WORKTREE_ADD_RE = /\bgit\s+worktree\s+add\b/;

function checkCommandSafety(command) {
  if (GIT_MAIN_PUSH_RE.test(command)) {
    return {
      safe: false,
      reason: "Direct push to main is forbidden. Use a feature branch and open a PR.",
    };
  }
  for (const p of FORBIDDEN_PATTERNS) {
    if (command.includes(p)) return { safe: false, reason: `Forbidden pattern: ${p}` };
  }
  if (GIT_COMMIT_RE.test(command) && !invokes(command, "gpc") && !invokes(command, "gpa")) {
    return {
      safe: false,
      reason:
        "Use 'gpc' (commit+push) or 'gpa --auto' (secrets scan + lint + AI review, then commit+push) instead of raw 'git commit'.",
    };
  }
  if (GH_PR_CREATE_RE.test(command) && !invokes(command, "gpr")) {
    return {
      safe: false,
      reason: "Use 'gpr <feat|fix> <branch-name>' instead of raw 'gh pr create'.",
    };
  }
  if (GH_PR_COMMENT_RE.test(command)) {
    return { safe: false, reason: "Posting PR comments from an agent session is forbidden." };
  }
  if (GH_PR_REVIEW_RE.test(command)) {
    return { safe: false, reason: "Submitting PR reviews from an agent session is forbidden." };
  }
  if (GH_PR_MERGE_RE.test(command)) {
    return { safe: false, reason: "Merging PRs from an agent session is forbidden." };
  }
  if (GIT_CHECKOUT_B_RE.test(command) && !invokes(command, "gpr")) {
    return {
      safe: false,
      reason: "Use 'gpr <feat|fix> <branch-name>' to create feature branches, not raw 'git checkout -b'.",
    };
  }
  if (GIT_WORKTREE_ADD_RE.test(command) && !invokes(command, "gpr")) {
    return {
      safe: false,
      reason: "Use 'gpr <feat|fix> <branch-name>' instead of raw 'git worktree add'.",
    };
  }
  return { safe: true };
}

const EDIT_TOOLS = new Set(["edit", "write", "patch"]);

export default async () => ({
  "tool.execute.before": async (input, output) => {
    const tool = input?.tool;
    const args = output?.args ?? input?.args ?? {};

    if (tool === "bash") {
      const command = typeof args.command === "string" ? args.command : "";
      const result = checkCommandSafety(command);
      if (!result.safe) throw new Error(`[git-workflow-guard] ${result.reason}`);
      return;
    }

    if (EDIT_TOOLS.has(tool)) {
      const filePath = typeof args.filePath === "string" ? args.filePath : "";
      if (!filePath) return;

      const found = await findGitRoot(filePath);
      if (found.error) {
        throw new Error(
          `[git-workflow-guard] ${found.error} — refusing to edit until this is resolved.`,
        );
      }
      if (!found.root) return; // not inside a git repo — nothing to enforce

      const mainCheck = await isMainWorktree(found.root);
      if (mainCheck.error) {
        throw new Error(
          `[git-workflow-guard] ${mainCheck.error} — refusing to edit until this is resolved.`,
        );
      }
      if (mainCheck.isMain) {
        throw new Error(
          `[git-workflow-guard] Editing directly in the primary repo checkout (${found.root}) is not allowed — it must stay on main. ` +
            `Run 'gpr' to create a worktree for this work, then edit there.`,
        );
      }
    }
  },
});
