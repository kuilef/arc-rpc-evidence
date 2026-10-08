# Arc RPC Evidence

Mode: **synthetic**
Endpoint: `offline fixture (official mainnet preset label; zero HTTP requests)`
Observation window: 2026-10-08T00:00:05.000+00:00 to 2026-10-08T00:00:05.000+00:00
Requests: **6/24** (every attempt, including retries/errors).
Socket timeout: 5s; deadline before new requests: 45s; response limit: 262144 bytes; targets: at most 3.
In-flight reads obey socket timeouts; DNS/TLS and a blocked read can extend wall time.
Stop reason: **completed bounded plan**

Synthetic fixture data, zero HTTP requests. Request counts below are simulated.

Chain: expected 5042; observed 5042; **verified**.
Head: **verified**. Pinned number/hash lookups agree.
Pinned head: block 100, `0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`.
Head age vs local clock: 5.0s (within-120s-of-local-clock).

## Transactions

- `0x1111111111111111111111111111111111111111111111111111111111111111`: **observed-null**; execution: unknown. Transaction or receipt was null. Pending, import lag or unavailable history are possible; absence and failure are not proven.

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
