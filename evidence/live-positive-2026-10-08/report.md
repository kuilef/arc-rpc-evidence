# Arc RPC Evidence

Mode: **live**
Endpoint: `https://rpc.mainnet.arc.io`
Observation window: 2026-10-08T21:32:24.305+00:00 to 2026-10-08T21:32:26.431+00:00
Requests: **8/9** (every attempt, including retries/errors).
Socket timeout: 5.0s; deadline before new requests: 45s; response limit: 262144 bytes; targets: at most 3.
In-flight reads obey socket timeouts; DNS/TLS and a blocked read can extend wall time.
Stop reason: **completed bounded plan**

Chain: expected 5042; observed 5042; **verified**.
Head: **verified**. Pinned number/hash lookups agree.
Pinned head: block 24964963, `0x604117c1e2672f73aa523028c2de08cbf348e261f25e7fb48ae24bcafc67eb66`.
Head age vs local clock: 1.374s (within-120s-of-local-clock).

## Transactions

- `0xae69b0c4dbf5e33cc4fad7794c4ae116c129bffc284a81dcb7444f0b2d9d717e`: **verified**; execution: succeeded. Receipt, transaction and pinned block inclusion agree at observation times.

## Method observations

| Method | Support observed |
| --- | --- |
| `eth_blockNumber` | observed-supported |
| `eth_chainId` | observed-supported |
| `eth_getBlockByHash` | observed-supported |
| `eth_getBlockByNumber` | observed-supported |
| `eth_getTransactionByHash` | observed-supported |
| `eth_getTransactionReceipt` | observed-supported |

## Request accounting

| Attempt | Method | Outcome | RPC/HTTP code |
| --- | --- | --- | --- |
| 1 | `eth_chainId` | ok |  |
| 2 | `eth_blockNumber` | ok |  |
| 3 | `eth_getBlockByNumber` | ok |  |
| 4 | `eth_getBlockByHash` | ok |  |
| 5 | `eth_getTransactionByHash` | ok |  |
| 6 | `eth_getTransactionReceipt` | ok |  |
| 7 | `eth_getBlockByNumber` | ok |  |
| 8 | `eth_getBlockByHash` | ok |  |

## Interpretation limits

- Timestamped endpoint observations; not an authoritative chain source or finality proof.
- Null does not prove absence, failure, pruning or endpoint misconduct.
- Header availability at selected blocks does not establish archive-state completeness.
- Near-tip changes may reflect backend import lag or changing chain observations.
- Head age depends on local clock; this run does not measure uptime, reliability or speed.
- `verified` means agreement among returned fields at the recorded times.
- `observed-null` records a null result; execution stays unknown.
- `insufficient-evidence` covers errors, malformed fields and unfinished checks.
- `inconsistent-observation` records disagreement; tip/import changes are possible.
- No speed leaderboard, reliability rating or misconduct claim follows from this report.

Published JSON retains only fields used by checks; unused addresses/logs/calldata omitted.

Selection used 3 additional reads; combined selection + CLI: 11/12 attempts.
