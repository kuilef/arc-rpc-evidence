# Validation record

Verified on 2026-10-08 with Python 3.12 on Windows.

- `python -m unittest -q`: 45 tests, zero failures/errors after the bounded follow-up.
- `python -m ruff check .`: passed.
- `python -m mypy`: strict check passed for seven source modules.
- `python -m build`: wheel and sdist built successfully using setuptools 83.0.0.
- Installed wheel CLI invoked outside the source directory: offline `tip-recover`
  demo completed, nine simulated attempts and zero HTTP requests.
- `python -m pip check`: no broken requirements.
- `pip-audit -r requirements-dev.txt`: no known vulnerabilities in the audit
  snapshot. See [machine-readable audit](dependency-audit.json). This is a
  point-in-time public advisory check, not a guarantee about unknown issues.
- Runtime dependencies: none. Development pins and action commits are explicit.
- Local credential-pattern scan: no private key headers, AWS access-key IDs or
  GitHub token patterns in tracked deliverables. Dummy URL credentials in
  restriction tests are intentional and never sent to any endpoint.

Independent fresh code review found three Important issues, all reproduced
offline and fixed with regression tests: initial hash response lost fields,
truncated HTTP body losing partial evidence, nonfinite JSON numeric overflow.
No Critical or deferred Minor findings remained from that review.

Live evidence is scoped to [one bounded run](live-2026-10-08/report.md): eight
requests on the official primary Arc endpoint, timestamped 21:09:32.373 through
21:09:34.559 UTC. Methods: chain identity, head number, block lookup by number/hash,
transaction lookup and receipt lookup. Head and genesis header comparisons agreed;
the deliberately zero transaction hash returned null. No real execution status,
archive-state completeness, uptime, reliability or speed was established.

Positive follow-up: [CLI report](live-positive-2026-10-08/report.md) and
[selection accounting](live-positive-2026-10-08/selection.json). Three official
reads selected the first transaction in one head-minus-four block (24964891),
then eight CLI reads verified the same pinned number/hash, receipt status `0x1`
and transaction inclusion. Total 11/12 attempts, 21:31:49.577..21:32:26.431 UTC.
Unused addresses, logs, calldata and other non-evidence fields are omitted from
the published JSON. This records endpoint agreement, not independent finality.

Additional review counterexample reproduced: successful RPC envelopes containing
empty/incomplete transaction/receipt objects incorrectly produced a pending
conflict. Schema is now validated first; the regression failed six assertions
before the fix, then passed. A valid pending transaction plus valid mined receipt
retains `inconsistent-observation` and unknown execution. Full suite 45/45 green.

No getLogs, signatures, wallet calls, transaction submissions, public services,
grant submissions or contacts were made. CI performs offline verification only.
CI links and exact checked commit are available in GitHub Actions; this file
records the local validation and is not a claim of an unobserved CI outcome.
