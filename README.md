# Arc RPC Evidence

A small read-only CLI for developers investigating a particular Arc receipt or
historical block lookup. It records what one official RPC endpoint returned,
checks internal agreement, and explains what the observations cannot prove.

```console
python -m arc_rpc_evidence demo --scenario null-receipt
```

**No wallet, API key or runtime dependencies. Python 3.11+.**
[Русская инструкция](MANUAL_RU.md) · [Grant preparation](GRANTS_RU.md)

## Install and run

```console
git clone https://github.com/kuilef/arc-rpc-evidence.git
cd arc-rpc-evidence
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` on Windows, or
`source .venv/bin/activate` on Linux/macOS. Then:

```console
python -m pip install --no-deps .
arc-rpc-evidence demo --scenario healthy --output reports/demo
arc-rpc-evidence demo --scenario null-receipt --output reports/null
arc-rpc-evidence check --preset mainnet --block 0 --budget 12 --output reports/live
```

For a specific transaction replace the example hash below with a public hash.
Use at most three `--tx`/`--block` targets combined. Block targets accept decimal
numbers, canonical hex quantities, or 32-byte hashes. No targets checks genesis.

```console
arc-rpc-evidence check --tx 0x0000000000000000000000000000000000000000000000000000000000000000 --budget 12
arc-rpc-evidence check --block 100 --block 200 --output reports/history
arc-rpc-evidence check --help
```

The console report and exports show timestamps, the pinned head, local-clock
head age, method observations and every request attempt. `report.json` retains
returned block/transaction/receipt fields; `report.md` explains the verdicts.
Exports never overwrite existing files. Exit 0 means a report was produced,
even when evidence is incomplete; 2 means invalid input/export failure;
130 means cancelled with a partial report. Ctrl+C cancels the current run.

## What the verdicts mean

| Verdict | Interpretation |
| --- | --- |
| `verified` | Returned fields agree for the requested identifiers, block hash/number and transaction inclusion at observation times. No independent trust or finality proof. |
| `observed-null` | A relevant query returned null. It does not establish absence, failed execution or pruning. |
| `insufficient-evidence` | Error, malformed fields, missing observations, cancellation or exhausted budget prevented verification. |
| `inconsistent-observation` | Returned observations disagree. Tip changes and backend import lag can be transient causes; no endpoint misconduct claim. |

`execution: failed` is reported only when status `0x0` and inclusion checks agree.
A verified failed transaction is a valid outcome of the checks. Null or incomplete
checks leave execution unknown. Block header availability is scoped to each target;
this CLI does not test archive-state completeness. Method support describes only
the methods exercised, including observed unsupported `-32601` responses.

## Visible bounds and safe defaults

- One fixed anonymous preset: `https://rpc.mainnet.arc.io`, expected chain 5042.
  Wrong or unverified identity stops before other RPC methods.
- At most 24 attempts per invocation, including retries and errors. `--budget`
  can reduce it to 1..24. Three targets maximum; sequential requests only.
- Socket timeout defaults to 5 seconds and can only be lowered. A 45-second
  deadline is checked before starting each attempt. Reads have a byte/time guard;
  DNS/TLS and an in-flight blocked socket can extend wall time.
- Responses are capped at 256 KiB. One 250ms retry for `-32014` only within two
  blocks of the observed tip; pinned near-tip disagreement gets one repeat.
- No URL input, private-address probes, file URL reads, HTTP redirects, environment
  proxy routing, credentials, keys, write methods, server or background monitor.
  Export paths are explicit local CLI destinations, not remote URL inputs.

Arc documents anonymous/open-CORS primary access, load-balanced near-tip
`-32014`, and a `-32012` log-range limit. This MVP sends **no `eth_getLogs`**;
the oversized-range error is tested offline. See
[official RPC reference](https://docs.arc.io/arc/references/rpc-endpoints) and
[network configuration](https://docs.arc.io/arc/references/connect-to-arc).

## Offline replay and evidence

Scenarios: `healthy`, `null-receipt`, `null-transaction`, `failed-receipt`,
`missing-block`, `conflict`, `tip-recover`, `tip-stop`, `rate-limit`, `timeout`,
`malformed`, `wrong-chain`. Demo requests are simulated; actual HTTP count is zero.

[Synthetic null demo](evidence/demo-null/report.md) and
[timestamped mainnet smoke](evidence/live-2026-10-08/report.md) are separate.
The recorded smoke made eight reads: identity/head/pinned head, genesis by
number/hash, zero-hash transaction/receipt. It observed mainnet identity, consistent
headers and null transaction data. It did not verify a real transaction's execution.

## Development

```console
python -m pip install -r requirements-dev.txt
python -m unittest -v
python -m ruff check .
python -m mypy
python -m build
python -m pip check
```

CI runs offline tests, lint, strict typing, package build and installed CLI demo
on Python 3.11/3.12 and Linux/Windows. CI does not call mainnet. Tests cover wrong
identity, null/pending, failed receipts, missing blocks, malformed envelopes,
contradictory hash/inclusion, near-tip recovery/stop, 429/timeouts, cancellation,
budgets, restricted endpoints and local exports.

## Prior art and scope

[GetBlock's RPC benchmark](https://github.com/GetBlock-io/rpc-endpoint-benchmark)
documents latency, reliability and workload comparison.
[arctools](https://github.com/ilkermanap/arctools) provides Arc linting,
USDC indexing and an agent registry, including a rate-limited RPC client.
This project focuses on explaining the limits of a few receipt/header observations
with replayable failure cases. The overlap is acknowledged; no absolute uniqueness
claim or provider ranking is intended. Own code under [MIT](LICENSE).
