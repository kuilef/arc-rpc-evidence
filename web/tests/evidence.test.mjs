import test from "node:test";
import assert from "node:assert/strict";
import { createHttpTransport, runCheck, parsePayload, blockId } from "../public/evidence.mjs";
import { parseStrict } from "../public/json.mjs";
const tx = "0x" + "1".repeat(64), hash = "0x" + "a".repeat(64);
const head = { number: "0x64", hash, timestamp: "0x6553f100", transactions: [tx] };
const options = { clock: () => 1700000005000, monotonic: () => 0, sleep: async () => {} };
function transport(overrides = {}) {
  return async (method, params) => {
    if (Object.hasOwn(overrides, method)) return overrides[method];
    const result = method === "eth_chainId" ? "0x13b2" : method === "eth_blockNumber" ? "0x64" :
      method === "eth_getTransactionByHash" ? { hash: tx, blockNumber: "0x64", blockHash: hash, transactionIndex: "0x0" } :
      method === "eth_getTransactionReceipt" ? { transactionHash: tx, blockNumber: "0x64", blockHash: hash, transactionIndex: "0x0", status: "0x1" } :
      params[0] === "0x0" ? { ...head, number: "0x0", transactions: [] } : head;
    return { status: "ok", result };
  };
}
test("A successful receipt is verified only with matching transaction and pinned inclusion", async () => {
  const report = await runCheck({ kind: "transaction", target: tx }, transport(), options);
  assert.equal(report.target.verdict, "verified"); assert.equal(report.target.execution, "succeeded");
  assert.equal(report.request_count, 8); assert.equal(report.observations.length, 8);
  const mismatch = await runCheck({ kind: "transaction", target: tx }, transport({
    eth_getTransactionReceipt: { status: "ok", result: { transactionHash: "0x" + "2".repeat(64), blockNumber: "0x64", blockHash: hash, transactionIndex: "0x0", status: "0x1" } },
  }), options);
  assert.equal(mismatch.target.verdict, "inconsistent-observation"); assert.equal(mismatch.target.execution, "unknown");
});
test("Null and errored receipts do not establish failed execution", async () => {
  for (const response of [{ status: "ok", result: null }, { status: "timeout" }, { status: "rate-limit" }]) {
    const report = await runCheck({ kind: "transaction", target: tx }, transport({ eth_getTransactionReceipt: response }), options);
    assert.equal(report.target.execution, "unknown");
    assert.equal(report.target.verdict, response.status === "ok" ? "observed-null" : "insufficient-evidence");
  }
});
test("Verified status zero is failed execution, not an RPC failure", async () => {
  const report = await runCheck({ kind: "transaction", target: tx }, transport({
    eth_getTransactionReceipt: { status: "ok", result: { transactionHash: tx, blockNumber: "0x64", blockHash: hash, transactionIndex: "0x0", status: "0x0" } },
  }), options);
  assert.equal(report.target.verdict, "verified"); assert.equal(report.target.execution, "failed");
});
test("Wrong network stops before all nonidentity methods", async () => {
  const report = await runCheck({ kind: "block", target: "0" }, transport({ eth_chainId: { status: "ok", result: "0x1" } }), options);
  assert.equal(report.request_count, 1); assert.equal(report.stop_reason, "chain-mismatch");
});
test("Strict envelopes reject duplicate decoded keys, nonfinite and unsafe numbers", () => {
  for (const value of [
    '{"jsonrpc":"2.0","id":1,"id":1,"result":null}',
    String.raw`{"jsonrpc":"2.0","id":1,"\u0069d":1,"result":null}`,
    '{"jsonrpc":"2.0","id":1,"result":1e400}',
    '{"jsonrpc":"2.0","id":1,"result":9007199254740993}',
    '{"jsonrpc":"2.0","id":2,"result":null}',
    '{"jsonrpc":"2.0","id":1,"result":null,"error":{}}',
  ]) assert.equal(parsePayload(value, 1).status, "malformed", value);
  assert.equal(parsePayload('{"jsonrpc":"2.0","id":1,"result":null}', 1).status, "ok");
  assert.throws(() => parseStrict("\vnull"));
  assert.throws(() => blockId("18446744073709551616"));
  assert.throws(() => blockId("0X1"));
  assert.equal(blockId("18446744073709551615"), "0xffffffffffffffff");
});
test("HTTP transport has one fixed origin, rejects write methods and bounds response bytes", async () => {
  const called = [];
  const call = createHttpTransport(async (url, init) => {
    called.push(url); assert.equal(init.redirect, "error"); assert.equal(init.credentials, "omit");
    const body = JSON.parse(init.body);
    return Response.json({ jsonrpc: "2.0", id: body.id, result: "0x13b2" });
  });
  assert.equal((await call("eth_chainId", [], 5000)).status, "ok");
  await assert.rejects(() => call("eth_sendRawTransaction", ["0x00"], 5000));
  assert.deepEqual(called, ["https://rpc.mainnet.arc.io"]);
  const oversized = createHttpTransport(async () => new Response("x", { headers: { "Content-Length": "262145" } }));
  assert.equal((await oversized("eth_chainId", [], 5000)).status, "response-too-large");
});
test("Browser cancellation produces a partial report", async () => {
  const controller = new AbortController(); controller.abort();
  const report = await runCheck({ kind: "block", target: "0" }, transport(), { ...options, signal: controller.signal });
  assert.equal(report.request_count, 0); assert.equal(report.stop_reason, "cancelled");
  assert.equal(report.target.verdict, "insufficient-evidence");
});
test("Envelope IDs and error codes require lexical integer tokens, matching the CLI", () => {
  for (const value of [
    '{"jsonrpc":"2.0","id":1.0,"result":null}',
    '{"jsonrpc":"2.0","id":1e0,"result":null}',
    '{"jsonrpc":"2.0","id":1,"error":{"code":-32601.0}}',
    '{"jsonrpc":"2.0","id":1,"error":{"code":-32601e0}}',
  ]) assert.equal(parsePayload(value, 1).status, "malformed", value);
  assert.equal(parsePayload('{"jsonrpc":"2.0","id":1,"result":{"id":1.0,"error":{"code":1.5}}}', 1).status, "ok");
});
test("Depth, invalid UTF-8 and streamed size limits reject malformed provider data", async () => {
  assert.throws(() => parseStrict("[".repeat(66) + "null" + "]".repeat(66)));
  const invalid = createHttpTransport(async () => new Response(new Uint8Array([0xff])));
  assert.equal((await invalid("eth_chainId", [], 5000)).status, "malformed");
  const streamed = createHttpTransport(async () => new Response(new ReadableStream({
    start(controller) { controller.enqueue(new Uint8Array(262145)); controller.close(); },
  })));
  assert.equal((await streamed("eth_chainId", [], 5000)).status, "response-too-large");
});
test("Transport distinguishes bounded timeout and cancellation, without retrying 429", async () => {
  const pending = async (_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
  });
  assert.equal((await createHttpTransport(pending)("eth_chainId", [], 5)).status, "timeout");
  const controller = new AbortController();
  const cancelled = createHttpTransport(pending, controller.signal)("eth_chainId", [], 5000);
  controller.abort();
  assert.equal((await cancelled).status, "cancelled");
  let count = 0;
  const report = await runCheck({ kind: "block", target: "0" }, createHttpTransport(async () => {
    count++; return new Response("", { status: 429 });
  }), options);
  assert.equal(count, 1); assert.equal(report.request_count, 1);
  assert.equal(report.stop_reason, "chain-unverified");
  assert.equal(report.target.verdict, "insufficient-evidence");
});
test("Deadline and cancellation after an attempt retain honest partial accounting", async () => {
  let now = 0;
  const deadline = await runCheck({ kind: "transaction", target: tx }, async () => {
    now = 45000; return { status: "ok", result: "0x13b2" };
  }, { ...options, monotonic: () => now });
  assert.equal(deadline.stop_reason, "deadline"); assert.equal(deadline.request_count, 1);
  assert.equal(deadline.observations.length, 1); assert.equal(deadline.target.execution, "unknown");
  const controller = new AbortController();
  const cancelled = await runCheck({ kind: "transaction", target: tx }, async () => {
    controller.abort(); return { status: "cancelled" };
  }, { ...options, signal: controller.signal });
  assert.equal(cancelled.stop_reason, "cancelled"); assert.equal(cancelled.request_count, 1);
  assert.equal(cancelled.observations[0].status, "cancelled");
});
test("Near-tip errors use one bounded repeat while historical errors never retry", async () => {
  const base = transport(); let errors = 0;
  const retry = await runCheck({ kind: "transaction", target: tx }, async (method, params) => {
    if (method === "eth_getBlockByNumber" && errors++ === 0) return { status: "rpc-error", code: -32014 };
    return base(method, params);
  }, options);
  assert.equal(retry.target.verdict, "verified"); assert.equal(retry.request_count, 9);
  assert.equal(retry.observations[3].attempt, 2);
  const old = await runCheck({ kind: "block", target: "1" }, async (method, params) => {
    if (method === "eth_getBlockByNumber" && params[0] === "0x1") return { status: "rpc-error", code: -32014 };
    return base(method, params);
  }, options);
  assert.equal(old.target.verdict, "insufficient-evidence"); assert.equal(old.request_count, 5);
});
test("Provider disagreement cannot exceed the twelve-attempt request budget", async () => {
  const base = transport(); let numberCalls = 0, hashCalls = 0;
  const report = await runCheck({ kind: "transaction", target: tx }, async (method, params) => {
    if (method === "eth_getBlockByNumber") {
      numberCalls++;
      if ([1, 3, 5].includes(numberCalls)) return { status: "rpc-error", code: -32014 };
    }
    if (method === "eth_getBlockByHash") {
      hashCalls++;
      if ([1, 3, 5].includes(hashCalls)) return { status: "rpc-error", code: -32014 };
      if (hashCalls === 2) return { status: "ok", result: { ...head, timestamp: "0x1" } };
    }
    return base(method, params);
  }, options);
  assert.equal(report.request_count, 12); assert.equal(report.observations.length, 12);
  assert.equal(report.stop_reason, "request-budget");
  assert.equal(report.target.execution, "unknown");
});
test("Malformed, missing and mismatched transaction fields never establish execution", async () => {
  for (const result of [ {}, [], {hash: tx},
    {hash: tx, blockNumber: null, blockHash: null, transactionIndex: null},
    {hash: tx, blockNumber: "0x64", blockHash: hash, transactionIndex: "0x1"},
  ]) {
    const report = await runCheck({ kind: "transaction", target: tx }, transport({eth_getTransactionByHash: {status:"ok", result}}), options);
    assert.notEqual(report.target.verdict, "verified"); assert.equal(report.target.execution, "unknown");
  }
});
