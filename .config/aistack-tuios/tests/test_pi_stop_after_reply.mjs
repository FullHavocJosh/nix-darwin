const mod = await import(new URL("../pi-stop-after-reply.ts", import.meta.url));

// Create a fake pi object
const fakePi = {
  on: (name, fn) => {
    fakePi.handlers[name] = fn;
  },
  handlers: {}
};

// Track abort calls
let abortCalls = 0;
const fakeCtx = {
  abort: () => {
    abortCalls++;
  }
};

// Register the handler
mod.default(fakePi);

// Get the tool_result handler
const toolResultHandler = fakePi.handlers["tool_result"];

// Test cases
let passed = 0;
let failed = 0;

// Test 1: abort for bash, isError false, command `tuios send-agent-message -w plan --reply-to 19 'done: added x'`
abortCalls = 0;
toolResultHandler({
  toolName: "bash",
  isError: false,
  input: { command: "tuios send-agent-message -w plan --reply-to 19 'done: added x'" }
}, fakeCtx);
if (abortCalls === 1) {
  passed++;
} else {
  failed++;
  console.log("FAIL: Test 1 - Expected abort call for done message");
}

// Test 2: abort for the same with 'blocked: no access'
abortCalls = 0;
toolResultHandler({
  toolName: "bash",
  isError: false,
  input: { command: "tuios send-agent-message -w plan --reply-to 19 'blocked: no access'" }
}, fakeCtx);
if (abortCalls === 1) {
  passed++;
} else {
  failed++;
  console.log("FAIL: Test 2 - Expected abort call for blocked message");
}

// Test 3: abort with double quotes: "done: added x"
abortCalls = 0;
toolResultHandler({
  toolName: "bash",
  isError: false,
  input: { command: 'tuios send-agent-message -w plan --reply-to 19 "done: added x"' }
}, fakeCtx);
if (abortCalls === 1) {
  passed++;
} else {
  failed++;
  console.log("FAIL: Test 3 - Expected abort call for double quoted done message");
}

// Test 4: no abort for bash `ls -la`
abortCalls = 0;
toolResultHandler({
  toolName: "bash",
  isError: false,
  input: { command: "ls -la" }
}, fakeCtx);
if (abortCalls === 0) {
  passed++;
} else {
  failed++;
  console.log("FAIL: Test 4 - Expected no abort for ls command");
}

// Test 5: no abort for bash `echo done: tuios`
abortCalls = 0;
toolResultHandler({
  toolName: "bash",
  isError: false,
  input: { command: "echo done: tuios" }
}, fakeCtx);
if (abortCalls === 0) {
  passed++;
} else {
  failed++;
  console.log("FAIL: Test 5 - Expected no abort for echo command");
}

// Test 6: no abort for the done mail when isError is true
abortCalls = 0;
toolResultHandler({
  toolName: "bash",
  isError: true,
  input: { command: "tuios send-agent-message -w plan --reply-to 19 'done: added x'" }
}, fakeCtx);
if (abortCalls === 0) {
  passed++;
} else {
  failed++;
  console.log("FAIL: Test 6 - Expected no abort for isError true");
}

// Test 7: no abort for toolName "read" whose input.command holds the done mail
abortCalls = 0;
toolResultHandler({
  toolName: "read",
  isError: false,
  input: { command: "tuios send-agent-message -w plan --reply-to 19 'done: added x'" }
}, fakeCtx);
if (abortCalls === 0) {
  passed++;
} else {
  failed++;
  console.log("FAIL: Test 7 - Expected no abort for read tool");
}

// Test 8: Verify the module registers a handler for "tool_result" and nothing else
if (Object.keys(fakePi.handlers).length === 1 && fakePi.handlers["tool_result"]) {
  passed++;
} else {
  failed++;
  console.log("FAIL: Test 8 - Expected only tool_result handler");
}

console.log(`Passed: ${passed}, Failed: ${failed}`);

if (failed > 0) {
  process.exit(1);
} else {
  console.log("PASS");
}