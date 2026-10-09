import { parseStrict } from "./json.mjs";
export const ENDPOINT = "https://rpc.mainnet.arc.io";
export const isHash = value => typeof value === "string" && /^0x[0-9a-fA-F]{64}$/.test(value);
export const quantity = value => typeof value === "string" && /^0x(?:0|[1-9a-fA-F][0-9a-fA-F]{0,15})$/.test(value) ? BigInt(value) : null;
export function blockId(value) {
  if (typeof value !== "string") throw Error("invalid_block");
  let n = quantity(value);
  if (n === null && /^(?:0|[1-9]\d{0,19})$/.test(value)) n = BigInt(value);
  if (n === null || n >= 2n ** 64n) throw Error("invalid_block");
  return "0x" + n.toString(16);
}
const validBlock = value => value && typeof value === "object" && !Array.isArray(value) &&
  quantity(value.number) !== null && isHash(value.hash) && quantity(value.timestamp) !== null &&
  Array.isArray(value.transactions) && value.transactions.every(isHash);
const finding = target => ({ target, verdict: "insufficient-evidence", execution: "unknown", detail: "Not enough observations to verify this target." });
const equalTransactions = (a, b) => a.length === b.length && a.every((tx, i) => tx.toLowerCase() === b[i].toLowerCase());

export function parsePayload(text, id) {
  try {
    const data = parseStrict(text, (_value, token, path) => {
      // JSON.parse otherwise loses the distinction between 1, 1.0 and 1e0.
      const envelopeInteger = (path.length === 1 && path[0] === "id") ||
        (path.length === 2 && path[0] === "error" && path[1] === "code");
      if (envelopeInteger && !/^-?(?:0|[1-9]\d*)$/.test(token)) throw Error("integer_token_required");
    });
    if (!data || typeof data !== "object" || Array.isArray(data) ||
        data.jsonrpc !== "2.0" || data.id !== id || !Number.isSafeInteger(data.id) ||
        Object.hasOwn(data, "result") === Object.hasOwn(data, "error")) return { status: "malformed" };
    if (Object.hasOwn(data, "result")) return { status: "ok", result: data.result };
    if (!data.error || typeof data.error !== "object" || Array.isArray(data.error) ||
        !Number.isSafeInteger(data.error.code)) return { status: "malformed" };
    return { status: "rpc-error", code: data.error.code };
  } catch { return { status: "malformed" }; }
}
export function createHttpTransport(fetcher = fetch, outerSignal) {
  let sequence = 0;
  return async (method, params, timeoutMs) => {
    const valid = ["eth_chainId", "eth_blockNumber"].includes(method) ? params.length === 0 :
      ["eth_getTransactionByHash", "eth_getTransactionReceipt"].includes(method) ? params.length === 1 && isHash(params[0]) :
      ["eth_getBlockByNumber", "eth_getBlockByHash"].includes(method) && params.length === 2 && params[1] === false &&
        (method.endsWith("Hash") ? isHash(params[0]) : quantity(params[0]) !== null);
    if (!valid || !(timeoutMs > 0 && timeoutMs <= 5000)) throw Error("invalid_rpc_read");
    const controller = new AbortController();
    const cancel = () => controller.abort();
    outerSignal?.addEventListener("abort", cancel, { once: true });
    if (outerSignal?.aborted) cancel();
    const timer = setTimeout(cancel, timeoutMs);
    const id = ++sequence;
    try {
      const response = await fetcher(ENDPOINT, {
        method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id, method, params }),
        redirect: "error", credentials: "omit", referrerPolicy: "no-referrer", signal: controller.signal,
      });
      if (!response.ok) return { status: response.status === 429 ? "rate-limit" : "http-error", http_status: response.status };
      if (Number(response.headers.get("Content-Length")) > 262144) return { status: "response-too-large" };
      const reader = response.body?.getReader();
      if (!reader) return { status: "malformed" };
      const chunks = []; let size = 0;
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        size += value.length;
        if (size > 262144) { await reader.cancel(); return { status: "response-too-large" }; }
        chunks.push(value);
      }
      const bytes = new Uint8Array(size); let at = 0;
      for (const chunk of chunks) { bytes.set(chunk, at); at += chunk.length; }
      try { return parsePayload(new TextDecoder("utf-8", { fatal: true }).decode(bytes), id); }
      catch { return { status: "malformed" }; }
    } catch {
      return { status: outerSignal?.aborted ? "cancelled" : controller.signal.aborted ? "timeout" : "network-error" };
    } finally {
      clearTimeout(timer); controller.abort();
      outerSignal?.removeEventListener("abort", cancel);
    }
  };
}
export async function runCheck(options, transport, {
  clock = () => Date.now(), monotonic = () => performance.now(), signal,
  sleep = ms => new Promise(resolve => setTimeout(resolve, ms)),
} = {}) {
  const kind = options.kind ?? "block";
  if (!["block", "transaction"].includes(kind)) throw Error("invalid_target_kind");
  if (kind === "transaction" && !isHash(options.target)) throw Error("invalid_transaction_hash");
  const target = kind === "transaction" ? options.target.toLowerCase() : blockId(options.target ?? "0");
  const started = monotonic();
  const report = {
    schema_version: "browser-1", mode: "live-browser", endpoint: ENDPOINT,
    started_at: new Date(clock()).toISOString(), finished_at: null, request_count: 0,
    limits: { max_targets: 1, request_budget: 12, timeout_seconds: 5, deadline_seconds: 45,
      max_response_bytes: 262144, tip_retries: 1, json_depth: 64 },
    chain: { expected: 5042, observed: null, verdict: "insufficient-evidence" },
    head: finding("observed-head"), target: finding(target), method_support: {}, observations: [],
    stop_reason: null,
    limits_of_evidence: [
      "Provider observations, not an independent trust or finality proof.",
      "Null does not prove absence, failure, pruning or endpoint misconduct.",
      "Selected header availability does not establish archive-state completeness.",
      "Near-tip changes may reflect backend import lag or changing observations.",
      "Browser transport cannot distinguish redirect rejection from other fetch failures.",
      "Single target; decimal block numbers or canonical hex only. Use Python CLI for block hashes or multiple targets.",
    ],
  };
  let headNumber = null;
  const STOP = Symbol("stop");
  const near = n => n !== null && headNumber !== null && headNumber >= n && headNumber - n <= 2n;
  async function call(method, params, tip = false) {
    for (let attempt = 1; attempt <= (tip ? 2 : 1); attempt++) {
      const left = 45000 - (monotonic() - started);
      if (signal?.aborted || left <= 0 || report.request_count >= 12) {
        report.stop_reason = signal?.aborted ? "cancelled" : left <= 0 ? "deadline" : "request-budget";
        throw STOP;
      }
      const observedAt = new Date(clock()).toISOString(); report.request_count++;
      const result = await transport(method, params, Math.min(5000, left));
      report.observations.push({ request: report.request_count, method, params, attempt,
        observed_at: observedAt, completed_at: new Date(clock()).toISOString(), ...result });
      if (result.status === "ok") report.method_support[method] = "observed-supported";
      else if (result.code === -32601) report.method_support[method] = "observed-unsupported";
      else report.method_support[method] ??= "unknown";
      if (result.status === "cancelled") { report.stop_reason = "cancelled"; throw STOP; }
      if (result.code !== -32014 || attempt === 2 || !tip) return result;
      await sleep(250);
    }
  }
  async function pair(first, expectedNumber, expectedHash) {
    if (first.status !== "ok") return { verdict: "insufficient-evidence", detail: "Block query errored." };
    const a = first.result;
    if (a === null) return { verdict: "observed-null", detail: "Block query returned null; reason unknown." };
    if (!validBlock(a)) return { verdict: "insufficient-evidence", detail: "Malformed block fields." };
    const number = quantity(a.number), hash = a.hash.toLowerCase();
    if (number !== expectedNumber || (expectedHash && hash !== expectedHash.toLowerCase())) {
      return { verdict: "inconsistent-observation", detail: "Returned block differs from requested identifier." };
    }
    const pinned = await call("eth_getBlockByHash", [hash, false], near(number)), b = pinned.result;
    if (pinned.status !== "ok" || !validBlock(b)) return {
      verdict: pinned.status === "ok" && b === null ? "observed-null" : "insufficient-evidence",
      detail: "Pinned hash lookup unavailable or malformed.",
    };
    let matches = b.hash.toLowerCase() === hash && quantity(b.number) === number &&
      b.timestamp === a.timestamp && equalTransactions(b.transactions, a.transactions);
    if (!matches && near(number)) {
      const repeated = await call("eth_getBlockByNumber", ["0x" + number.toString(16), false], true);
      const repeatedHash = await call("eth_getBlockByHash", [hash, false], true);
      const c = repeated.result, d = repeatedHash.result;
      if (repeated.status !== "ok" || repeatedHash.status !== "ok" || !validBlock(c) || !validBlock(d)) {
        return { verdict: "insufficient-evidence", detail: "Near-tip repeat unavailable." };
      }
      // CLI's near-tip repeat uses literal timestamp/transaction list equality.
      matches = c.hash.toLowerCase() === hash && d.hash.toLowerCase() === hash &&
        quantity(c.number) === number && quantity(d.number) === number &&
        c.timestamp === d.timestamp && d.timestamp === a.timestamp &&
        JSON.stringify(c.transactions) === JSON.stringify(d.transactions) &&
        JSON.stringify(d.transactions) === JSON.stringify(a.transactions);
    }
    return { verdict: matches ? "verified" : "inconsistent-observation",
      detail: matches ? "Pinned number/hash lookups agree." : "Pinned observations disagree after a bounded repeat where applicable.",
      number_decimal: number.toString(), hash, timestamp_hex: a.timestamp };
  }
  async function transaction() {
    const result = finding(target);
    const tx = await call("eth_getTransactionByHash", [target]), receipt = await call("eth_getTransactionReceipt", [target]);
    if (tx.status !== "ok" || receipt.status !== "ok") return { ...result, detail: "Transaction or receipt query errored; execution remains unknown." };
    const a = tx.result, b = receipt.result;
    if (a === null || b === null) return { ...result, verdict: "observed-null", detail: "Transaction or receipt was null. Absence and failure are not proven." };
    if (!a || !b || typeof a !== "object" || typeof b !== "object" || Array.isArray(a) || Array.isArray(b)) return result;
    if (!isHash(a.hash) || !isHash(b.transactionHash) || !isHash(b.blockHash) ||
        quantity(b.blockNumber) === null || quantity(b.transactionIndex) === null || !["0x0", "0x1"].includes(b.status)) return result;
    if (["blockNumber", "blockHash", "transactionIndex"].every(key => Object.hasOwn(a, key) && a[key] === null)) {
      return { ...result, verdict: "inconsistent-observation", detail: "Pending transaction conflicts with a mined receipt; sequential observations may change." };
    }
    if (!isHash(a.blockHash) || quantity(a.blockNumber) === null || quantity(a.transactionIndex) === null) return result;
    const number = quantity(a.blockNumber);
    if (a.hash.toLowerCase() !== target || b.transactionHash.toLowerCase() !== target ||
        a.blockHash.toLowerCase() !== b.blockHash.toLowerCase() || quantity(b.blockNumber) !== number ||
        quantity(a.transactionIndex) !== quantity(b.transactionIndex)) {
      return { ...result, verdict: "inconsistent-observation", detail: "Transaction/receipt identifiers or position disagree; no misconduct conclusion." };
    }
    const header = await call("eth_getBlockByNumber", [a.blockNumber, false], near(number));
    const checked = await pair(header, number, a.blockHash);
    Object.assign(result, checked);
    if (checked.verdict === "verified") {
      const index = quantity(a.transactionIndex), list = header.result.transactions;
      if (index >= BigInt(list.length) || list[Number(index)].toLowerCase() !== target) {
        Object.assign(result, { verdict: "inconsistent-observation", detail: "Requested transaction is absent at the observed index." });
      } else Object.assign(result, { execution: b.status === "0x1" ? "succeeded" : "failed", detail: "Receipt, transaction and pinned block inclusion agree at observation times." });
    }
    return result;
  }
  try {
    const chain = await call("eth_chainId", []), chainId = chain.status === "ok" ? quantity(chain.result) : null;
    report.chain.observed = chainId === null ? null : chainId.toString();
    if (chainId !== 5042n) {
      report.stop_reason = chainId === null ? "chain-unverified" : "chain-mismatch";
      if (chainId !== null) report.chain.verdict = "inconsistent-observation";
      return report;
    }
    report.chain.verdict = "verified";
    const head = await call("eth_blockNumber", []); headNumber = head.status === "ok" ? quantity(head.result) : null;
    if (headNumber === null) { report.stop_reason = "head-unverified"; return report; }
    report.head = { ...report.head, ...await pair(await call("eth_getBlockByNumber", ["0x" + headNumber.toString(16), false], true), headNumber) };
    if (report.head.verdict !== "verified") { report.stop_reason = "head-unverified"; return report; }
    if (kind === "transaction") report.target = await transaction();
    else report.target = { ...report.target, ...await pair(await call("eth_getBlockByNumber", [target, false], near(quantity(target))), quantity(target)) };
  } catch (e) {
    if (e !== STOP) throw e;
  } finally { report.finished_at = new Date(clock()).toISOString(); }
  return report;
}
