// @ts-nocheck
// aidev builder: once the builder has mailed its one-line done or blocked reply, abort the agent so the local model cannot loop (summary, checks, mail again).
const REPLY = /\btuios\s+send-agent-message\b[\s\S]*?['"](?:done|blocked):/;

export default function (pi) {
  pi.on("tool_result", (event, ctx) => {
    if (event.toolName !== "bash" || event.isError === true) {
      return;
    }

    const command = String(event.input?.command ?? "");
    if (REPLY.test(command)) {
      ctx.abort();
    }
  });
}
