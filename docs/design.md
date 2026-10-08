# Arc RPC Evidence design

Developer-facing, read-only CLI to explain a few Arc mainnet RPC observations.
Python 3.11+, standard library runtime, MIT, one official primary preset.
No URL input, wallet, signing, proxy server, deployment, continuous polling or
endpoint ranking. Build in an isolated new repository.

Inputs: up to three transaction hashes/block numbers/block hashes combined.
No targets defaults to genesis header availability. Chain identity is checked
first; wrong/unknown identity stops. A head number is pinned to its header and
hash, then looked up by hash. Receipt and transaction fields are compared to
the requested hash, pinned block hash/number and transaction list. Historical
block availability only describes the requested headers; no archive claims.
Method support only covers methods actually called. Head age is relative to
local wall clock and is never an uptime assertion.

Every attempted HTTP call counts, including retries and errors. Budget 24,
timeout 5s, wall deadline 45s, response cap 256KiB; smaller CLI budgets allowed.
Retry -32014 once only near the observed tip (within two blocks), after 250ms.
One repeated pinned comparison is allowed for near-tip conflicting observations.
No 429 retries. Abort on Ctrl+C with a partial report. HTTP redirects refused.
Missing/null/error/malformed/support outcomes are recorded independently from
verified/observed-null/insufficient-evidence/inconsistent-observation verdicts.
Verified means internally consistent at observed times, not trusted finality.

Offline synthetic fixtures exercise wrong chain, null transaction/receipt,
failed receipt, missing block, hash conflict, near-tip recover/stop, 429,
timeout, malformed payload, limits, cancellation and restricted endpoints.
Large getLogs range error -32012 is a local fixture only. MVP sends no getLogs.
CLI and report tests, ruff, strict mypy, wheel/sdist build, bounded live smoke,
dependency/secret review, GitHub CI on exact final commit are the gates.

User explicitly authorized autonomous narrow design, implementation and new
public repository publication; no additional overnight questions or approval
gates. Grant submission and public hosting remain user-only steps.
