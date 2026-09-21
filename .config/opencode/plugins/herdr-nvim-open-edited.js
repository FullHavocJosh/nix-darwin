// Ported from the Claude Code PostToolUse hook at
// ~/nix-darwin/scripts/herdr-nvim-open-edited.sh
//
// Mirrors edited files into the sibling "nvim" pane of the same herdr tab,
// the way tuicr already surfaces them for review. `:edit` only swaps the
// current window's buffer -- it never closes other tabs -- and nvim's
// default 'hidden' is on, so it doesn't matter whether the target buffer
// already has unsaved changes.

import { execFile } from "node:child_process";

const EDIT_TOOLS = new Set(["edit", "write", "patch"]);

function run(cmd, args) {
  return new Promise((resolve) => {
    execFile(cmd, args, { timeout: 3000 }, (err, stdout) => {
      resolve({ err, stdout: stdout ?? "" });
    });
  });
}

async function findNvimPane(workspaceId, tabId) {
  const { err, stdout } = await run("herdr", [
    "pane",
    "list",
    "--workspace",
    workspaceId,
  ]);
  if (err) return undefined;
  try {
    const parsed = JSON.parse(stdout);
    const panes = parsed?.result?.panes ?? [];
    const match = panes.find((p) => p.label === "nvim" && p.tab_id === tabId);
    return match?.pane_id;
  } catch {
    return undefined;
  }
}

function escapeVimString(path) {
  return path.replace(/'/g, "''");
}

export default async () => {
  if (
    process.env.HERDR_ENV !== "1" ||
    !process.env.HERDR_WORKSPACE_ID ||
    !process.env.HERDR_TAB_ID
  ) {
    return {};
  }

  return {
    "tool.execute.after": async (input) => {
      if (!EDIT_TOOLS.has(input.tool)) return;

      const filePath = input.args?.filePath;
      if (!filePath) return;

      const paneId = await findNvimPane(
        process.env.HERDR_WORKSPACE_ID,
        process.env.HERDR_TAB_ID,
      );
      if (!paneId) return;

      const escaped = escapeVimString(filePath);
      await run("herdr", ["pane", "send-keys", paneId, "esc"]);
      await run("herdr", [
        "pane",
        "send-text",
        paneId,
        `:execute 'edit ' . fnameescape('${escaped}')`,
      ]);
      await run("herdr", ["pane", "send-keys", paneId, "enter"]);
    },
  };
};
