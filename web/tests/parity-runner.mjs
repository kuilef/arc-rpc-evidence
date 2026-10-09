import assert from "node:assert/strict";
import { runCheck } from "../public/evidence.mjs";
let data = "";
for await (const chunk of process.stdin) data += chunk;
const cases = JSON.parse(data);
for (const item of cases) {
  const trace = structuredClone(item.trace);
  const transport = async (method, params) => {
    const expected = trace.shift();
    assert.ok(expected, item.scenario + ": unexpected extra request");
    assert.equal(method, expected.method, item.scenario);
    assert.deepEqual(params, expected.params, item.scenario);
    const response = { status: expected.status };
    for (const key of ["result", "code", "http_status"]) if (Object.hasOwn(expected, key)) response[key] = expected[key];
    return response;
  };
  const report = await runCheck({ kind: item.kind, target: item.target }, transport, {
    clock: () => 1791417605000, monotonic: () => 0, sleep: async () => {},
  });
  assert.equal(trace.length, 0, item.scenario + ": observations were discarded");
  assert.deepEqual({
    chain: report.chain.verdict, head: report.head.verdict,
    target: report.target.verdict, execution: report.target.execution,
    request_count: report.request_count, stop_reason: report.stop_reason, method_support: report.method_support,
  }, item.expected, item.scenario);
  process.stdout.write(item.scenario + " parity passed\n");
}
