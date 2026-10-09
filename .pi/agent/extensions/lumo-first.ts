// Lumo first: every message typed into pi goes to Lumo (lumo-tamer) before the local model sees it.
//
//   - Lumo's answer is printed as it came back. The local model never relays it: a 9b model shortens and
//     distorts what it repeats.
//   - Lumo ends each answer with "LOCAL: no" or "LOCAL: yes - <what to do>". Only on "yes" does the local model
//     run, with Lumo's answer in its context. Lumo cannot read files or run commands; the local model can.
//   - The local model has one extra tool, ask_lumo, to hand what it read back to Lumo.
//   - A message that starts with ";" skips Lumo and goes straight to the local model.
//
// The tamer is found in the same order as _aistack_tier0 in .zshrc_functions_ai: this machine's own
// (127.0.0.1:3003, key from ~/lumo-tamer/config.yaml), MacMiniM1's on the home network, then the public
// endpoint, both with keys from Doppler. PI_LUMO_URL / PI_LUMO_KEY pin one endpoint. PI_LUMO_FIRST=0 turns the
// extension off. When no tamer answers, the message goes to the local model unchanged.
//
// aidev does not load this file: it runs pi with its own PI_CODING_AGENT_DIR.

import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import path from "node:path";
import { Type } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const SKIP_PREFIX = ";";
const MODEL = process.env.PI_LUMO_MODEL || "lumo";
const TIMEOUT_MS = Number(process.env.PI_LUMO_TIMEOUT_S || 180) * 1000;
const HISTORY_MAX = 24; // messages kept for Lumo; older ones are dropped

const SYSTEM = `You are the main assistant in a terminal chat. Answer the user directly and concisely, in plain text or markdown.

You cannot read the user's files or run commands. A small local assistant on the user's machine can: it reads files, runs shell commands and edits files, and it reports back what it found.

End every answer with one final line, exactly one of:
LOCAL: no
LOCAL: yes - <one or two sentences telling the local assistant what to read, run or change>

Use "LOCAL: yes" only when the answer depends on the user's files or machine, or when the user asks for a change there. For everything else answer in full and use "LOCAL: no". Never write tool calls or JSON yourself.`;

type Turn = { role: "user" | "assistant"; content: string };
type Tamer = { url: string; key: string };

function doppler(name: string, config: string): Promise<string> {
  return new Promise((resolve) => {
    execFile(
      "doppler",
      [
        "secrets",
        "get",
        name,
        "--project",
        "FullHavocJosh",
        "--config",
        config,
        "--plain",
      ],
      { timeout: 8000 },
      (error, stdout) => resolve(error ? "" : stdout.trim()),
    );
  });
}

async function localKey(): Promise<string> {
  try {
    const text = await readFile(
      path.join(homedir(), "lumo-tamer", "config.yaml"),
      "utf8",
    );
    return /^\s*apiKey:\s*"(.*)"\s*$/m.exec(text)?.[1] ?? "";
  } catch {
    return "";
  }
}

async function answers(tamer: Tamer): Promise<boolean> {
  try {
    const response = await fetch(`${tamer.url}/models`, {
      headers: tamer.key ? { Authorization: `Bearer ${tamer.key}` } : {},
      signal: AbortSignal.timeout(4000),
    });
    return response.status === 200;
  } catch {
    return false;
  }
}

async function findTamer(): Promise<Tamer | undefined> {
  if (process.env.PI_LUMO_URL) {
    const pinned = {
      url: process.env.PI_LUMO_URL.replace(/\/$/, ""),
      key: process.env.PI_LUMO_KEY || "",
    };
    return (await answers(pinned)) ? pinned : undefined;
  }
  const candidates: Array<() => Promise<Tamer>> = [
    async () => ({ url: "http://127.0.0.1:3003/v1", key: await localKey() }),
    async () => ({
      url: "http://macminim1.rollet.family:3003/v1",
      key: await doppler("LUMO_TAMER_API_KEY", "root_macmini"),
    }),
    async () => ({
      url: "https://lumo.rollet.family/v1",
      key: await doppler("LUMO_PUBLIC_API_KEY", "root_hetzner-cluster"),
    }),
  ];
  for (const candidate of candidates) {
    const tamer = await candidate();
    if (tamer.key && (await answers(tamer))) return tamer;
  }
  return undefined;
}

// Splits Lumo's answer from its trailing LOCAL line. No marker counts as "no": the answer still reaches the user.
function splitMarker(text: string): {
  answer: string;
  local: string | undefined;
} {
  const match =
    /\n?^[ \t>*`]*LOCAL:\s*(yes|no)\b[ \t]*[-:–]?[ \t]*(.*?)[ \t*`]*$/im.exec(
      text,
    );
  if (!match) return { answer: text.trim(), local: undefined };
  const answer = (
    text.slice(0, match.index) + text.slice(match.index + match[0].length)
  ).trim();
  if (match[1].toLowerCase() === "no") return { answer, local: undefined };
  return { answer, local: match[2].trim() || "Do what the user asked." };
}

export default function (pi: ExtensionAPI) {
  if (process.env.PI_LUMO_FIRST === "0") return;

  let tamer: Promise<Tamer | undefined> | undefined;
  let history: Turn[] = [];
  let pending: string | undefined; // Lumo's answer for the turn the local model is about to run

  async function askLumo(
    question: string,
    signal?: AbortSignal,
  ): Promise<string> {
    tamer ??= findTamer();
    const found = await tamer;
    if (!found) {
      tamer = undefined; // probe again on the next message
      throw new Error("no lumo-tamer answered");
    }
    history.push({ role: "user", content: question });
    history = history.slice(-HISTORY_MAX);
    const timeout = AbortSignal.timeout(TIMEOUT_MS);
    let text = "";
    try {
      const response = await fetch(`${found.url}/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${found.key}`,
        },
        body: JSON.stringify({
          model: MODEL,
          messages: [{ role: "system", content: SYSTEM }, ...history],
        }),
        signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
      });
      if (!response.ok)
        throw new Error(`lumo-tamer answered ${response.status}`);
      const body = (await response.json()) as {
        choices?: Array<{ message?: { content?: string } }>;
      };
      text = body.choices?.[0]?.message?.content?.trim() ?? "";
      if (!text) throw new Error("lumo-tamer returned an empty answer");
    } catch (error) {
      history.pop(); // the question got no answer, so Lumo's history must not keep it
      throw error;
    }
    history.push({ role: "assistant", content: text });
    return text;
  }

  pi.on("session_start", async () => {
    history = [];
    pending = undefined;
  });

  pi.on("input", async (event, ctx) => {
    if (event.source === "extension") return { action: "continue" };
    const text = event.text.trim();
    if (!text || text.startsWith("/") || text.startsWith("!"))
      return { action: "continue" };
    if (text.startsWith(SKIP_PREFIX)) {
      return {
        action: "transform",
        text: text.slice(SKIP_PREFIX.length).trim(),
        images: event.images,
      };
    }

    ctx.ui.setStatus("lumo", "asking Lumo...");
    let reply: string;
    try {
      reply = await askLumo(text, ctx.signal);
    } catch (error) {
      ctx.ui.notify(
        `Lumo skipped (${(error as Error).message}); the local model answers.`,
        "warning",
      );
      return { action: "continue" };
    } finally {
      ctx.ui.setStatus("lumo", undefined);
    }

    const { answer, local } = splitMarker(reply);
    if (local === undefined) {
      // The local model does not run, so the question is recorded here for its later context.
      if (ctx.mode === "print") console.log(answer);
      await pi.sendMessage({
        customType: "lumo",
        content: `> ${text}\n\nLumo: ${answer}`,
        display: true,
      });
      return { action: "handled" };
    }
    if (ctx.mode === "print") console.log(`Lumo: ${answer}\n`);
    pending = `Lumo: ${answer}\n\nLumo asks the local assistant: ${local}`;
    return { action: "continue" };
  });

  pi.on("before_agent_start", async () => {
    if (!pending) return;
    const content = pending;
    pending = undefined;
    return { message: { customType: "lumo", content, display: true } };
  });

  // What the local model found goes into Lumo's history, so a follow-up question to Lumo can use it.
  pi.on("agent_end", async (event) => {
    const last = event.messages.findLast(
      (message) => message.role === "assistant",
    );
    if (!last || !Array.isArray(last.content)) return;
    const text = last.content
      .flatMap((block) => (block.type === "text" ? [block.text] : []))
      .join("\n")
      .trim();
    if (text)
      history.push({
        role: "user",
        content: `[The local assistant reported]\n${text.slice(0, 8000)}`,
      });
  });

  pi.registerTool({
    name: "ask_lumo",
    label: "Ask Lumo",
    description:
      "Ask Lumo, the stronger remote model, a question. Lumo cannot see files: put the relevant file content or command output in the question.",
    promptSnippet:
      "ask_lumo: send a question, with the file content or output it needs, to the stronger Lumo model",
    promptGuidelines: [
      "A message that starts with 'Lumo:' is Lumo's answer and the user has already read it. Never repeat or rephrase it.",
      "Your job is the tool work Lumo asks for: read, run or edit, then report what you found in a few lines.",
      "When what you found needs explaining, judging or planning, call ask_lumo with the findings instead of reasoning yourself.",
    ],
    parameters: Type.Object({
      question: Type.String({
        description:
          "The question, with the file content or command output Lumo needs",
      }),
    }),
    async execute(_toolCallId, params, signal) {
      try {
        const { answer } = splitMarker(await askLumo(params.question, signal));
        return { content: [{ type: "text", text: answer }], details: {} };
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `Lumo is not reachable: ${(error as Error).message}`,
            },
          ],
          details: {},
          isError: true,
        };
      }
    },
  });
}
