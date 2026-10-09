"""Compare browser verdicts and request selection with the existing Python diagnostic."""
import json
import shutil
import subprocess
from pathlib import Path

from arc_rpc_evidence.demo import SCENARIOS, demo_report

node = shutil.which("node")
if node is None:
    raise SystemExit("Node.js 22 is required for browser parity checks.")
cases = []
for scenario in SCENARIOS:
    report = demo_report(scenario, budget=12)
    target = (report["blocks"] or report["transactions"])[0]
    cases.append({
        "scenario": scenario,
        "kind": "block" if report["blocks"] else "transaction",
        "target": target["target"],
        "trace": report["observations"],
        "expected": {
            "chain": report["chain"]["verdict"],
            "head": report["head"]["verdict"],
            "target": target["verdict"],
            "execution": target["execution"],
            "request_count": report["request_count"],
            "stop_reason": report["stop_reason"],
            "method_support": report["method_support"],
        },
    })
runner = Path(__file__).with_name("parity-runner.mjs")
subprocess.run([node, str(runner)], input=json.dumps(cases), text=True, check=True)  # noqa: S603
