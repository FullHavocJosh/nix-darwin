// @ts-nocheck
// aidev builder: never read a big file whole (one read of aidev_tuios.py fills a third of the context) and never read
// the mailbox (the typed prompt names the task file, which holds the whole task).
import { statSync } from "node:fs";
import { resolve } from "node:path";

const CAP = Number(process.env.AIDEV_READ_CAP_BYTES || 20000);
const MAX_LINES = 200;
const MAILBOX = /\btuios\s+read-agent-messages\b/;
const CAT = /^\s*cat\s+([^\s|;&<>]+)\s*$/;

function sizeOf(path, ctx) {
  try {
    return statSync(resolve(ctx?.cwd || process.cwd(), path)).size;
  } catch {
    return undefined;
  }
}

function wholeReason(path, size) {
  return `${path} is ${Math.round(size / 1024)} KB: never read it whole. Find the region with rg -n 'name' ${path}, then read it with offset and limit (at most ${MAX_LINES} lines).`;
}

export default function (pi) {
  pi.on("tool_call", (event, ctx) => {
    try {
      const input = event.input;
      if (event.toolName === "read") {
        const size = sizeOf(input.path, ctx);
        if (size === undefined || size <= CAP) {
          return;
        }
        if (input.limit === undefined && input.offset === undefined) {
          return { block: true, reason: wholeReason(input.path, size) };
        }
        if (input.limit === undefined || input.limit > MAX_LINES) {
          input.limit = MAX_LINES;
        }
        return;
      }

      if (event.toolName === "bash") {
        const command = String(input?.command);
        if (MAILBOX.test(command)) {
          return {
            block: true,
            reason:
              "Do not read your mailbox: the typed prompt names the task file, which holds the whole task.",
          };
        }
        const m = CAT.exec(command);
        if (m) {
          const size = sizeOf(m[1], ctx);
          if (size !== undefined && size > CAP) {
            return { block: true, reason: wholeReason(m[1], size) };
          }
        }
      }
    } catch {
      return undefined;
    }
    return undefined;
  });
}
