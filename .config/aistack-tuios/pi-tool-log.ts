// @ts-nocheck
import { createHash } from "node:crypto";
import { appendFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

export default function (pi) {
  pi.on("tool_result", (event, ctx) => {
    const logPath = process.env.AIDEV_TOOL_LOG;
    if (!logPath) {
      return;
    }

    try {
      const timestamp = Date.now() / 1000;
      const tool = String(event.toolName);

      const args =
        event.input !== undefined ? JSON.stringify(event.input ?? null) : "{}";
      const argsHash = createHash("sha1")
        .update(args)
        .digest("hex")
        .substring(0, 16);

      let out = "";
      let outHash = "";

      if (event.content && Array.isArray(event.content)) {
        const textBlocks = event.content.filter(
          (block) => block.type === "text",
        );
        if (textBlocks.length > 0) {
          out = textBlocks.map((block) => block.text).join("");
          outHash = createHash("sha1")
            .update(out)
            .digest("hex")
            .substring(0, 16);
        }
      } else if (typeof event.content === "string") {
        out = event.content;
        outHash = createHash("sha1").update(out).digest("hex").substring(0, 16);
      }

      const logLine =
        JSON.stringify({
          ts: timestamp,
          tool: tool,
          args: argsHash,
          out: outHash,
        }) + "\n";

      const logDir = dirname(logPath);
      mkdirSync(logDir, { recursive: true });
      appendFileSync(logPath, logLine);
    } catch (e) {
      // Handler should never throw
    }
  });
}
