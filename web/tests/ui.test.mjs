// DOM-only offline tests: these do not exercise browser networking, CORS or layout.
import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { JSDOM } from "jsdom";
const tx = "0x" + "1".repeat(64), hash = "0x" + "a".repeat(64), genesisHash = "0x" + "b".repeat(64);
const head = { number: "0x64", hash, timestamp: "0x6553f100", transactions: [tx] };
const genesis = { ...head, number: "0x0", hash: genesisHash, transactions: [] };
const eventually = async predicate => {
  for (let i = 0; i < 100; i++) { if (predicate()) return; await new Promise(resolve => setTimeout(resolve, 5)); }
  assert.fail("DOM state did not settle");
};
test("UI keeps one run, preserves reports, cancels, reruns and exports honest observations", async () => {
  const html = await readFile(new URL("../public/index.html", import.meta.url), "utf8");
  const dom = new JSDOM(html, { url: "https://offline-ui-test.invalid/" });
  const originals = { document: globalThis.document, fetch: globalThis.fetch,
    createObjectURL: URL.createObjectURL, revokeObjectURL: URL.revokeObjectURL };
  const get = id => dom.window.document.getElementById(id);
  const downloads = [], requests = [];
  let pending = false;
  globalThis.document = dom.window.document;
  globalThis.fetch = async (url, init) => {
    const body = JSON.parse(init.body); requests.push(body);
    assert.equal(url, "https://rpc.mainnet.arc.io");
    if (pending) return new Promise((_resolve, reject) => init.signal.addEventListener("abort", () => reject(Error("cancelled")), { once: true }));
    const result = body.method === "eth_chainId" ? "0x13b2" : body.method === "eth_blockNumber" ? "0x64" :
      body.method === "eth_getTransactionByHash" ? {hash: tx, blockNumber:"0x64", blockHash:hash, transactionIndex:"0x0"} :
      body.method === "eth_getTransactionReceipt" ? {transactionHash:tx, blockNumber:"0x64",blockHash:hash,transactionIndex:"0x0",status:"0x1", note:"<script>unexpected()</script>"} :
      body.params[0] === "0x0" || body.params[0] === genesisHash ? genesis : head;
    return Response.json({ jsonrpc: "2.0", id: body.id, result });
  };
  URL.createObjectURL = blob => { downloads.push({blob}); return "blob:offline-test"; };
  URL.revokeObjectURL = () => {};
  dom.window.HTMLAnchorElement.prototype.click = function () { downloads.at(-1).name = this.download; };
  const submit = () => get("check").dispatchEvent(new dom.window.Event("submit", {bubbles:true, cancelable:true}));
  try {
    await import("../public/app.mjs");
    assert.equal(requests.length, 0); assert.equal(get("results").hidden, true);
    submit(); await eventually(() => !get("run").disabled);
    assert.equal(requests.length, 6); assert.equal(get("verdict").textContent, "verified");
    assert.match(get("scope").textContent, /Target: 0x0/);
    const firstReport = get("raw").textContent;
    get("target").value = "invalid"; submit(); await eventually(() => !get("run").disabled);
    assert.equal(requests.length, 6); assert.equal(get("raw").textContent, firstReport);
    assert.match(get("notice").textContent, /Previous report remains available/);
    get("kind").value = "transaction"; get("kind").dispatchEvent(new dom.window.Event("change"));
    assert.equal(get("target").value, ""); get("target").value = tx;
    pending = true; submit();
    assert.equal(get("kind").disabled, true); assert.equal(get("target").disabled, true);
    submit(); assert.equal(requests.length, 7, "Repeated submit must not begin another read");
    get("cancel").click(); await eventually(() => !get("run").disabled);
    const partial = JSON.parse(get("raw").textContent);
    assert.equal(partial.stop_reason, "cancelled"); assert.equal(partial.request_count, 1);
    assert.equal(partial.target.execution, "unknown"); assert.equal(get("cancel").disabled, true);
    assert.equal(get("target").disabled, false); assert.equal(get("kind").disabled, false);
    pending = false; submit(); await eventually(() => !get("run").disabled);
    const final = JSON.parse(get("raw").textContent);
    assert.equal(final.target.verdict, "verified"); assert.equal(final.target.execution, "succeeded");
    assert.equal(final.request_count, 8); assert.equal(get("raw").children.length, 0);
    assert.match(get("scope").textContent, new RegExp("Target: " + tx));
    get("json").click(); get("markdown").click();
    assert.deepEqual(downloads.map(x=>x.name), ["arc-rpc-evidence-browser.json", "arc-rpc-evidence-browser.md"]);
    assert.deepEqual(JSON.parse(await downloads[0].blob.text()), final);
    const markdown = await downloads[1].blob.text();
    assert.match(markdown, /Verdict: verified/); assert.match(markdown, /Execution: succeeded/);
    assert.match(markdown, /not an independent trust or finality proof/);
    assert.equal(dom.window.localStorage.length, 0); assert.equal(dom.window.sessionStorage.length, 0);
  } finally {
    globalThis.document = originals.document; globalThis.fetch = originals.fetch;
    URL.createObjectURL = originals.createObjectURL; URL.revokeObjectURL = originals.revokeObjectURL;
    dom.window.close();
  }
});
