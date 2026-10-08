# Execution ledger: docs/superpowers/plans/2026-10-08-arc-rpc-evidence.md

Execution: isolated new Windows repository.
No applicable AGENTS.md found in the workspace or parent task directories.
Ruling: autonomous design and implementation gates were already authorized by
the delegated user instruction; no overnight clarification/approval prompts.
Cost if wrong: design revisions in this small new repository.
Ruling: MVP has only a CLI and primary mainnet preset, no server/custom URL.
Reason: completes the requested evidence workflow with fewer exposure paths.
Cost if wrong: users preferring a browser need a future UI.
Ruling: socket timeout plus deadline checked before new requests are documented
explicitly; the program does not promise a hard wall deadline during DNS/TLS or
blocked socket reads. Cost if wrong: a run may last longer than 45 seconds.

Task 1: 19 core tests RED (27 failed assertions), then GREEN. Eight transport
tests RED (27 failed assertions), then full suite 27/27 GREEN. Ruff and strict
mypy passed after adding a valid-block TypeGuard and audited fixed-URL S310 note.
Task 2: six CLI tests RED, then full suite 33/33 GREEN, lint/types passed.
Offline demo report generated with no network transport; simulated 6 attempts.
Live smoke: 2026-10-08 21:09:32.373..21:09:34.559 UTC, 8/12 HTTP attempts,
only rpc.mainnet.arc.io. Chain 5042, pinned head+genesis headers agreed,
zero transaction/receipt hashes returned null. No writes, logs, real wallet,
transactions, credentials, deployment or grants submission.

Official Arc docs, community grant rules and DoraHacks detail page read directly.
DoraHacks web parser failed 405; browser displayed official rule text and deadline.
Readonly local CLI eligibility remains unconfirmed. Teams may submit distinct
projects; multiple solo payouts are not explicitly confirmed.

Final fresh review: no Critical, three Important. All fixed with RED→GREEN
regressions: first hash reply identity/timestamp/transaction list retained;
HTTPException/IncompleteRead captured with preceding observations and exact
count; nested +/- overflowing JSON floats rejected before export. Full suite
43/43 GREEN, lint and strict types pass. No deferred minor findings.
Dependency audit found PYSEC-2026-3447 in development/build setuptools 80.9.0;
updated only this project's pins to fixed 83.0.0. Runtime dependencies remain zero.
