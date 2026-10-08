# Arc RPC Evidence Implementation Plan

> **For agentic workers:** Execute inline using superpowers:executing-plans.

**Goal:** Explain bounded Arc RPC receipt and history evidence with an offline demo.
**Architecture:** Typed Python stdlib transport, bounded runner and CLI renderers.
**Tech Stack:** Python 3.11+, unittest, ruff, mypy, setuptools/build.
**Spec:** docs/design.md

## Global Constraints

- Mainnet 5042, only https://rpc.mainnet.arc.io preset; no URL input or redirects.
- 24 requests maximum, three targets, timeout 5s, deadline 45s, 256KiB response.
- Retry -32014 once near tip only; no live large log queries, writes or wallets.
- MIT, English README, Russian launch/grant manuals, CI and exact-commit evidence.

## Review Focus

- Malformed quantities/hash fields must never become verified.
- Pending/null transaction and receipt must preserve unknown execution state.
- A stopped run must retain exact request accounting and partial observations.
- Block hash lookup must match both the pinned hash and number.
- Failed receipt status with consistent inclusion must be reported as failed.

### Task 1: Evidence engine and transport

Files: arc_rpc_evidence/core.py, transport.py, tests/test_core.py,
tests/test_transport.py, tests/helpers.py. Interfaces: run(CheckOptions,
Transport) -> Report dictionary; Transport.call(method, params, timeout) ->
RpcResult; resolve_preset(name) -> fixed HTTPS URL.

- [ ] Write behavior tests for the spec and review focus; run unittest RED.
- [ ] Implement the smallest runner/transport, then run all tests GREEN.
- [ ] Ruff and strict mypy; record outcomes and commit.

### Task 2: Replay and CLI reports

Files: demo.py, cli.py, report.py, __main__.py, tests/test_cli.py.
Interfaces: demo_transport(scenario) supplies bounded synthetic responses;
markdown(report) -> str; main(argv) -> exit status (0 produced, 2 invalid input).

- [ ] Write CLI/demo/export tests; run RED.
- [ ] Implement deterministic synthetic replay with zero network, text/JSON
  exports and Ctrl+C partial evidence; run all tests GREEN.
- [ ] Build wheel/sdist, smoke installed CLI and offline replay.

### Task 3: Docs, live evidence and publication

Files: README.md, MANUAL_RU.md, GRANTS_RU.md, LICENSE,
.github/workflows/ci.yml, evidence/*.json and *.md.

- [ ] Verify current sources/prior art; explain readonly eligibility uncertainty.
- [ ] Run bounded mainnet check; save timestamped evidence separately from demo.
- [ ] Full tests/lint/types/build, dependency and secret review.
- [ ] Fresh whole-project review; fix important findings with regression tests.
- [ ] Create absent public kuilef/arc-rpc-evidence and push authorized code.
- [ ] Wait for terminal CI on exact HEAD; report links and remaining manual steps.
