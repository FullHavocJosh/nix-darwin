// Companion to herdr-agent-state.js — kept as a separate file since that one
// is managed/overwritten by herdr's integration installer.
//
// herdr-agent-state.js only reports "idle" in response to a `session.idle`
// event, which fires for opencode's persistent/interactive session lifecycle.
// One-shot `opencode run` (used throughout this repo's gpa/gpc git
// automations) never reaches that state — it renders its answer and tears
// down the run's transient server instance instead, emitting
// `server.instance.disposed`, which herdr-agent-state.js doesn't handle. So
// the pane's last "working" report (from tool/chat activity) is never
// followed by an idle report, and herdr shows the pane stuck "working"
// forever after the opencode process has already exited.

import net from "node:net";

const SOURCE = "herdr:opencode";
const AGENT = "opencode";
let reportSeq = Date.now() * 1000;

function nextReportSeq() {
  reportSeq += 1;
  return reportSeq;
}

function request(method, params) {
  const paneId = process.env.HERDR_PANE_ID;
  const socketPath = process.env.HERDR_SOCKET_PATH;

  if (!paneId || !socketPath) {
    return Promise.resolve();
  }

  const requestId = `${SOURCE}:${Date.now()}:${Math.floor(
    Math.random() * 1_000_000,
  )
    .toString()
    .padStart(6, "0")}`;
  const req = {
    id: requestId,
    method,
    params: {
      pane_id: paneId,
      source: SOURCE,
      agent: AGENT,
      seq: nextReportSeq(),
      ...params,
    },
  };

  return new Promise((resolve) => {
    const client = net.createConnection(socketPath, () => {
      client.write(`${JSON.stringify(req)}\n`);
    });

    const finish = () => {
      client.destroy();
      resolve();
    };

    client.setTimeout(500, finish);
    client.on("data", finish);
    client.on("error", finish);
    client.on("end", finish);
    client.on("close", resolve);
  });
}

export const HerdrRunExitPlugin = async () => {
  if (
    process.env.HERDR_ENV !== "1" ||
    !process.env.HERDR_SOCKET_PATH ||
    !process.env.HERDR_PANE_ID
  ) {
    return {};
  }

  let disposed = false;

  return {
    event: async ({ event }) => {
      if (event?.type !== "server.instance.disposed" || disposed) {
        return;
      }
      disposed = true;
      await request("pane.report_agent", { state: "idle" });
    },
  };
};
