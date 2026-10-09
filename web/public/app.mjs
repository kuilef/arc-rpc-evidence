import { createHttpTransport, runCheck } from "./evidence.mjs";
const get = id => document.getElementById(id);
let report, controller;
function render(value) {
  report = value;
  get("results").hidden = false;
  get("verdict").textContent = value.target.verdict;
  get("detail").textContent = value.target.detail;
  get("execution").textContent = "Execution: " + value.target.execution;
  get("scope").textContent = "Target: " + value.target.target + " · Chain: " + value.chain.verdict + " · head: " + value.head.verdict +
    " · " + value.request_count + "/12 attempts · stop: " + (value.stop_reason ?? "completed") +
    " · collected " + value.finished_at;
  get("raw").textContent = JSON.stringify(value, null, 2);
}
get("check").addEventListener("submit", async event => {
  event.preventDefault();
  if (controller) return;
  controller = new AbortController();
  get("run").disabled = true; get("cancel").disabled = false;
  get("kind").disabled = true; get("target").disabled = true;
  get("notice").textContent = "Reading bounded public observations…";
  try {
    render(await runCheck({ kind: get("kind").value, target: get("target").value.trim() },
      createHttpTransport(fetch, controller.signal), { signal: controller.signal }));
    get("notice").textContent = "Report produced. Check the verdict and stop reason before drawing a conclusion.";
  } catch (error) {
    get("notice").textContent = "Read rejected: " + error.message + ". Previous report remains available.";
  } finally {
    controller = undefined; get("run").disabled = false; get("cancel").disabled = true;
    get("kind").disabled = false; get("target").disabled = false;
  }
});
get("cancel").addEventListener("click", () => controller?.abort());
get("kind").addEventListener("change", () => { get("target").value = get("kind").value === "block" ? "0" : ""; });
function download(name, data, type) {
  const url = URL.createObjectURL(new Blob([data], { type }));
  const link = document.createElement("a"); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
get("json").addEventListener("click", () => {
  if (report) download("arc-rpc-evidence-browser.json", JSON.stringify(report, null, 2), "application/json");
});
get("markdown").addEventListener("click", () => {
  if (!report) return;
  const text = [
    "# Arc RPC Evidence — browser observation", "",
    "Endpoint: " + report.endpoint, "Collected: " + report.started_at + " → " + report.finished_at,
    "Target: " + report.target.target, "Verdict: " + report.target.verdict,
    "Execution: " + report.target.execution, report.target.detail,
    "Attempts: " + report.request_count + "/12", "Stop reason: " + (report.stop_reason ?? "completed"), "",
    "## Limits", ...report.limits_of_evidence.map(value => "- " + value), "",
    "## Request observations", ...report.observations.map(value =>
      "- " + value.observed_at + " " + value.method + " " + value.status +
      (value.code === undefined ? "" : " code " + value.code)),
    "", "Raw returned fields are retained in the companion JSON. Browser schema is not the Python CLI schema.",
  ].join("\n");
  download("arc-rpc-evidence-browser.md", text, "text/markdown");
});
