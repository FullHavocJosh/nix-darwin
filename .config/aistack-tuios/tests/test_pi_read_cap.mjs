import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const mod = await import(new URL("../pi-read-cap.ts", import.meta.url));

// Create a fake pi object
const fakePi = {
  on: (name, fn) => {
    fakePi.handlers[name] = fn;
  },
  handlers: {}
};

// Register the handler
mod.default(fakePi);

const toolCallHandler = fakePi.handlers["tool_call"];

let passed = 0;
let failed = 0;

function check(ok, name) {
  if (ok) {
    passed++;
  } else {
    failed++;
    console.log("FAIL: " + name);
  }
}

const testDir = join(tmpdir(), 'aidev-rc-' + process.pid);
rmSync(testDir, { recursive: true, force: true });
mkdirSync(testDir, { recursive: true });
writeFileSync(join(testDir, 'big.txt'), 'x'.repeat(30000));
writeFileSync(join(testDir, 'small.txt'), 'y'.repeat(100));
const ctx = { cwd: testDir };

function call(toolName, input) {
  return toolCallHandler({ toolName, input }, ctx);
}

try {
  check(typeof toolCallHandler === 'function', "registers a tool_call handler");

  // read of a big file without offset or limit is blocked
  let res = call("read", { path: "big.txt" });
  check(res?.block === true && String(res.reason).includes("never read it whole")
    && String(res.reason).includes("rg -n"), "read big.txt whole is blocked");

  // read with an offset and no limit gets limit 200
  let input = { path: "big.txt", offset: 10 };
  res = call("read", input);
  check(res === undefined && input.limit === 200, "read big.txt with offset sets limit 200");

  // read with limit 500 is clamped to 200
  input = { path: "big.txt", limit: 500 };
  res = call("read", input);
  check(res === undefined && input.limit === 200, "read big.txt with limit 500 clamps to 200");

  // read of a small file is left alone
  input = { path: "small.txt" };
  res = call("read", input);
  check(res === undefined && JSON.stringify(input) === JSON.stringify({ path: "small.txt" }),
    "read small.txt is untouched");

  // mailbox read is blocked
  res = call("bash", { command: "tuios read-agent-messages -w x --unread" });
  check(res?.block === true, "tuios read-agent-messages is blocked");

  // cat of a big file is blocked
  res = call("bash", { command: "cat big.txt" });
  check(res?.block === true && String(res.reason).includes("never read it whole"), "cat big.txt is blocked");

  // rg on a big file is allowed
  res = call("bash", { command: "rg -n foo big.txt" });
  check(res === undefined, "rg -n foo big.txt is not blocked");

  // read of a missing file is left to read
  input = { path: "missing.txt" };
  res = call("read", input);
  check(res === undefined && input.limit === undefined, "read missing.txt returns undefined");
} finally {
  rmSync(testDir, { recursive: true, force: true });
}

console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);
if (failed > 0) {
  process.exit(1);
}
console.log("PASS");
