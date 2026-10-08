from typing import Any


def markdown(report: dict[str, Any]) -> str:
    limits = report["limits"]
    lines = ["# Arc RPC Evidence", "", f"Mode: **{report['mode']}**",
             f"Endpoint: `{report['endpoint']}`",
             f"Observation window: {report['started_at']} to {report['finished_at']}",
             f"Requests: **{report['request_count']}/{limits['request_budget']}** "
             "(every attempt, including retries/errors).",
             f"Socket timeout: {limits['timeout_seconds']}s; deadline before new requests: "
             f"{limits['deadline_seconds']}s; response limit: {limits['max_response_bytes']} bytes; "
             f"targets: at most {limits['max_targets']}.",
             "In-flight reads obey socket timeouts; DNS/TLS and a blocked read can extend wall time.",
             f"Stop reason: **{report['stop_reason'] or 'completed bounded plan'}**", ""]
    if report["mode"] == "synthetic":
        lines.extend(["Synthetic fixture data, zero HTTP requests. Request counts below are simulated.", ""])
    chain, head = report["chain"], report["head"]
    lines.extend([f"Chain: expected {chain['expected']}; observed {chain['observed']}; **{chain['verdict']}**.",
                  f"Head: **{head['verdict']}**. {head['detail']}"])
    if "hash" in head:
        lines.extend([f"Pinned head: block {head['number']}, `{head['hash']}`.",
                      f"Head age vs local clock: {head.get('age_seconds_local_clock', 'unknown')}s "
                      f"({head.get('freshness', 'unknown')})."])
    for label in ("transactions", "blocks"):
        if report[label]:
            lines.extend(["", f"## {label.capitalize()}", ""])
        for finding in report[label]:
            lines.extend([f"- `{finding['target']}`: **{finding['verdict']}**; "
                          f"execution: {finding.get('execution', 'unknown')}. {finding['detail']}"])
    lines.extend(["", "## Method observations", "", "| Method | Support observed |",
                  "| --- | --- |"])
    for method, support in sorted(report["method_support"].items()):
        lines.append(f"| `{method}` | {support} |")
    lines.extend(["", "## Request accounting", "", "| Attempt | Method | Outcome | RPC/HTTP code |",
                  "| --- | --- | --- | --- |"])
    for observation in report["observations"]:
        lines.append(f"| {observation['request']} | `{observation['method']}` | "
                     f"{observation['status']} | {observation.get('code', observation.get('http_status', ''))} |")
    lines.extend(["", "## Interpretation limits", ""])
    lines.extend(f"- {limit}" for limit in report["limits_of_evidence"])
    lines.extend(["- `verified` means agreement among returned fields at the recorded times.",
                  "- `observed-null` records a null result; execution stays unknown.",
                  "- `insufficient-evidence` covers errors, malformed fields and unfinished checks.",
                  "- `inconsistent-observation` records disagreement; tip/import changes are possible.",
                  "- No speed leaderboard, reliability rating or misconduct claim follows from this report.", ""])
    return "\n".join(lines)
