import { createHash } from 'node:crypto';
import { rmSync, writeFileSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const mod = await import(new URL("../pi-tool-log.ts", import.meta.url));

// Create a fake pi object
const fakePi = {
  on: (name, fn) => {
    fakePi.handlers[name] = fn;
  },
  handlers: {}
};

// Register the handler
mod.default(fakePi);

// Get the tool_result handler
const toolResultHandler = fakePi.handlers["tool_result"];

// Test cases
let passed = 0;
let failed = 0;

// Test 1: Verify the module registers a handler for "tool_result" and nothing else
if (Object.keys(fakePi.handlers).length === 1 && fakePi.handlers["tool_result"]) {
  passed++;
} else {
  failed++;
  console.log("FAIL: Test 1 - Expected only tool_result handler");
}

// Test 2: a bash result with text content writes one line with the right tool and 16-char args and out
const testDir = join(tmpdir(), 'aidev-tl-' + process.pid);
const testFile = join(testDir, 'log.jsonl');
try {
  process.env.AIDEV_TOOL_LOG = testFile;
  rmSync(testDir, { recursive: true, force: true });
  
  toolResultHandler({
    toolName: "bash",
    input: { command: "ls -la" },
    content: [{ type: 'text', text: "some output" }]
  });
  
  const content = readFileSync(testFile, 'utf8');
  const lines = content.trim().split('\n');
  if (lines.length === 1) {
    const data = JSON.parse(lines[0]);
    if (data.tool === "bash" && data.args.length === 16 && /^[0-9a-f]+$/.test(data.args) && 
        data.out.length === 16 && /^[0-9a-f]+$/.test(data.out)) {
      passed++;
    } else {
      failed++;
      console.log("FAIL: Test 2 - Expected valid JSON output with correct tool and hashes");
    }
  } else {
    failed++;
    console.log("FAIL: Test 2 - Expected single line output");
  }
  
  rmSync(testDir, { recursive: true, force: true });
} catch (e) {
  failed++;
  console.log("FAIL: Test 2 - Exception during test");
}

// Test 3: two identical calls give identical args
try {
  process.env.AIDEV_TOOL_LOG = testFile;
  rmSync(testDir, { recursive: true, force: true });
  
  toolResultHandler({
    toolName: "bash",
    input: { command: "ls -la" },
    content: [{ type: 'text', text: "some output" }]
  });
  
  toolResultHandler({
    toolName: "bash",
    input: { command: "ls -la" },
    content: [{ type: 'text', text: "some output" }]
  });
  
  const content = readFileSync(testFile, 'utf8');
  const lines = content.trim().split('\n');
  if (lines.length === 2) {
    const data1 = JSON.parse(lines[0]);
    const data2 = JSON.parse(lines[1]);
    if (data1.args === data2.args) {
      passed++;
    } else {
      failed++;
      console.log("FAIL: Test 3 - Expected identical args for identical inputs");
    }
  } else {
    failed++;
    console.log("FAIL: Test 3 - Expected two lines output");
  }
  
  rmSync(testDir, { recursive: true, force: true });
} catch (e) {
  failed++;
  console.log("FAIL: Test 3 - Exception during test");
}

// Test 4: empty content gives out ''
try {
  process.env.AIDEV_TOOL_LOG = testFile;
  rmSync(testDir, { recursive: true, force: true });
  
  toolResultHandler({
    toolName: "bash",
    input: { command: "ls -la" },
    content: []
  });
  
  const content = readFileSync(testFile, 'utf8');
  const lines = content.trim().split('\n');
  if (lines.length === 1) {
    const data = JSON.parse(lines[0]);
    if (data.out === "") {
      passed++;
    } else {
      failed++;
      console.log("FAIL: Test 4 - Expected empty out for empty content");
    }
  } else {
    failed++;
    console.log("FAIL: Test 4 - Expected single line output");
  }
  
  rmSync(testDir, { recursive: true, force: true });
} catch (e) {
  failed++;
  console.log("FAIL: Test 4 - Exception during test");
}

// Test 5: unset env writes nothing and does not throw
try {
  delete process.env.AIDEV_TOOL_LOG;
  toolResultHandler({
    toolName: "bash",
    input: { command: "ls -la" },
    content: [{ type: 'text', text: "some output" }]
  });
  passed++;
} catch (e) {
  failed++;
  console.log("FAIL: Test 5 - Expected no exception for unset env");
}

// Test 6: content as a plain string does not throw
try {
  process.env.AIDEV_TOOL_LOG = testFile;
  rmSync(testDir, { recursive: true, force: true });
  
  toolResultHandler({
    toolName: "bash",
    input: { command: "ls -la" },
    content: "plain string content"
  });
  
  const content = readFileSync(testFile, 'utf8');
  const lines = content.trim().split('\n');
  if (lines.length === 1) {
    const data = JSON.parse(lines[0]);
    if (data.out.length === 16 && /^[0-9a-f]+$/.test(data.out)) {
      passed++;
    } else {
      failed++;
      console.log("FAIL: Test 6 - Expected valid hash for string content");
    }
  } else {
    failed++;
    console.log("FAIL: Test 6 - Expected single line output");
  }
  
  rmSync(testDir, { recursive: true, force: true });
} catch (e) {
  failed++;
  console.log("FAIL: Test 6 - Exception during test");
}

console.log(`Passed: ${passed}, Failed: ${failed}`);

if (failed > 0) {
  process.exit(1);
} else {
  console.log("PASS");
}