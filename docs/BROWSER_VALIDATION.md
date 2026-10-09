# Browser deployment verification — 2026-10-09

Baseline: public `kuilef/arc-rpc-evidence` commit
`b536ae8e63e8259cea022523f27752ec49f2ca87`, with the prepared Cloudflare/browser patch
and the local fixes described below. No Python implementation files changed.

## Verified locally

Environment: Linux, Python 3.12.14, Node.js 24.19.0.

- Python unittest: 45/45 pass.
- Ruff 0.14.0: pass; strict mypy 1.18.2: pass (7 source files).
- Python wheel and sdist build: pass; installed-wheel `null-receipt` and
  `tip-recover` CLI demos: pass; pip dependency consistency: pass.
- Test-only npm dependency audit: zero reported vulnerabilities.
- Browser diagnostic tests: 14/14 pass. Coverage includes verified success/failure,
  null/error distinction, identity gating, strict envelope validation, byte/depth
  limits, malformed UTF-8, timeout/cancellation accounting, no 429 retry,
  bounded near-tip retry, historical no-retry, exact twelve-attempt cap and
  incomplete/mismatched transaction fields.
- Offline CLI/browser parity: all 12 existing Python demo scenarios pass for
  request methods/parameters/count, chain/head/target verdict, execution,
  stop reason and method support. These are synthetic replays, not live evidence.
- DOM-only test: passes initial no-network state, genesis report, invalid-input
  retention, target-kind reset, single-flight submit, cancel with partial report,
  successful rerun, visible target identity, text-only raw rendering and both
  downloads. This uses JSDOM as a development-only dependency.
- Wrangler 4.149.0 `deploy --dry-run`: pass, six static files, no bindings.
  This validates the optional Workers Static Assets configuration, not a Pages
  deployment or an authenticated Cloudflare account.
- Pages ZIP: exactly `_headers`, `app.mjs`, `evidence.mjs`, `index.html`,
  `json.mjs`, `style.css` at archive root; CRC test and byte-for-byte source
  comparison passed. No node_modules, keys, build tools, Python, RPC fixtures,
  server code or automatic background reads are deployed.

## Repairs made during review

1. JSON-RPC envelope IDs and error codes now reject decimal/exponent numeric
   tokens (`1.0`, `1e0`) just as the Python parser does. The regression first
   failed before the parser change and then passed. Raw result-number parsing
   remains distinct; ordinary finite, safe result numbers are accepted.
2. Every report now displays the actual checked target next to its status,
   preventing later input changes from visually relabeling old evidence.
3. Target inputs are locked during a run, repeated submission is ignored, and
   cancellation restores controls before the next run. DOM regression checks
   cover cancellation followed by a successful new run.

## Deliberate parity limits

See `CLOUDFLARE_RU.md` for full details. The browser accepts one numeric block or
one transaction, has a fixed budget of 12, and lacks CLI block-hash/multiple-target
support. Browser schema `browser-1` uses decimal strings for checked numbers and
hex timestamps; there is no local-clock head-age/freshness calculation. It is not
the CLI's schema or replay format. JSON depth is capped at 64 and unsafe integer
numbers are rejected; UTF-8 is required. The browser uses browser/OS networking,
cannot distinguish redirect rejection from other fetch network errors and may
have timers delayed when suspended. Simultaneous deadline/budget exhaustion has
different stop-reason precedence. Both keep incomplete evidence unverified.

## Hosted-browser validation — 2026-10-09

Public URL: https://arc-rpc-evidence.pages.dev/
Deployment ID: `3b9cc6d8-5e50-4812-bc49-b3517020633e`.
Published static assets are unchanged from the verified ZIP. The draft PR's
Python and browser diagnostic CI workflows passed on commit
`6000ed8a618c491c68d384c6fa55ca9e51f5cae0`.

The initial standalone Chromium test launch was blocked by local IPC restrictions.
A separately available cloud Chrome subsequently tested the actual deployed page
with unmodified live fetches:

- Genesis: target/chain/head verified, 6 attempts, completed
  `2026-10-09T09:55:20.990Z`.
- Public transaction
  `0x691405ed18faaf588878725c5df92a338cad75fdec5b1f38250d9073ae7ad9c4`:
  target verified, execution succeeded, chain/head verified, 8 attempts,
  completed `2026-10-09T09:56:24.674Z`.
- JSON download completed and parsed identically to the displayed report.
- A separate deployment check confirmed CSP, no-referrer, nosniff and no-store
  response headers. Browser live success also demonstrates that this origin's
  CSP/CORS path worked for the tested network and browser.

Another browser/network connection returned `network-error` on the initial
`eth_chainId` request. Its precise cause is unresolved; local extension/filter,
DNS/TLS/network, preflight or provider-path failures must be distinguished with
Console/Network evidence. One logical attempt does not count browser-managed
OPTIONS requests. No global availability guarantee follows from these samples.

Mobile layout, hosted Markdown export and hosted Cancel/rerun are not asserted
by the checks above; the automated DOM flow separately covers those controls.
Treat network failures as insufficient evidence, without fake live fixtures or
a speculative proxy. The previous CLI evidence remains historical and separate.
