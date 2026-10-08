# Arc RPC Evidence

Mode: **live**
Endpoint: `https://rpc.mainnet.arc.io`
Observation window: 2026-10-08T21:09:32.373+00:00 to 2026-10-08T21:09:34.559+00:00
Requests: **8/12** (every attempt, including retries/errors).
Socket timeout: 5.0s; deadline before new requests: 45s; response limit: 262144 bytes; targets: at most 3.
In-flight reads obey socket timeouts; DNS/TLS and a blocked read can extend wall time.
Stop reason: **completed bounded plan**

Chain: expected 5042; observed 5042; **verified**.
Head: **verified**. Pinned number/hash lookups agree.
Pinned head: block 24962259, `0xa5c9506a20290d1592786c3270dc227196ce2ac2cb395ab668c8f9b2a128a00f`.
Head age vs local clock: 1.514s (within-120s-of-local-clock).

## Transactions

- `0x0000000000000000000000000000000000000000000000000000000000000000`: **observed-null**; execution: unknown. Transaction or receipt was null. Pending, import lag or unavailable history are possible; absence and failure are not proven.

## Blocks

- `0x0`: **verified**; execution: unknown. Pinned number/hash lookups agree.

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
