"""Point-in-time evidence, never an endpoint score or a finality proof."""
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol, TypeGuard

PRESETS = {"mainnet": "https://rpc.mainnet.arc.io"}
MAX_REQUESTS = 24
MAX_TARGETS = 3
MAX_RESPONSE_BYTES = 262144
DEADLINE_SECONDS = 45
HASH = re.compile(r"0x[0-9a-fA-F]{64}\Z")
QUANTITY = re.compile(r"0x(?:0|[1-9a-fA-F][0-9a-fA-F]{0,15})\Z")


class Transport(Protocol):
    def call(self, method: str, params: list[Any], timeout: float) -> dict[str, Any]: ...


def resolve_preset(name: str) -> str:
    if name not in PRESETS:
        raise ValueError("Only the official 'mainnet' preset is allowed; URL input is disabled.")
    return PRESETS[name]


def quantity(value: Any) -> int | None:
    if isinstance(value, str) and QUANTITY.fullmatch(value):
        return int(value, 16)
    return None


def is_hash(value: Any) -> bool:
    return isinstance(value, str) and HASH.fullmatch(value) is not None


def block_id(value: str) -> str:
    if is_hash(value):
        return value.lower()
    number = quantity(value)
    if number is None and re.fullmatch(r"(?:0|[1-9][0-9]{0,19})", value):
        number = int(value)
    if number is None or number >= 2**64:
        raise ValueError("Block must be a nonnegative number or a 32-byte hash.")
    return hex(number)


def timestamp(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, UTC).isoformat(timespec="milliseconds")


def valid_block(value: Any) -> TypeGuard[dict[str, Any]]:
    return (isinstance(value, dict) and quantity(value.get("number")) is not None
            and is_hash(value.get("hash")) and quantity(value.get("timestamp")) is not None
            and isinstance(value.get("transactions"), list)
            and all(is_hash(item) for item in value["transactions"]))


def empty_finding(target: str) -> dict[str, Any]:
    return {"target": target, "verdict": "insufficient-evidence", "execution": "unknown",
            "detail": "Not enough observations to verify this target."}


class StopRun(Exception):
    pass


class Runner:
    def __init__(self, options: dict[str, Any], transport: Transport,
                 clock: Callable[[], float], monotonic: Callable[[], float],
                 sleep: Callable[[float], None]) -> None:
        preset = options.get("preset", "mainnet")
        endpoint = resolve_preset(preset)
        budget = options.get("budget", MAX_REQUESTS)
        timeout = options.get("timeout", 5.0)
        txs, blocks = options.get("transactions", []), options.get("blocks", [])
        if (not isinstance(budget, int) or isinstance(budget, bool) or not 1 <= budget <= 24
                or not isinstance(timeout, (int, float)) or isinstance(timeout, bool)
                or not 0 < timeout <= 5):
            raise ValueError("Budget must be 1..24; timeout must be >0 and <=5 seconds.")
        if not isinstance(txs, list) or not isinstance(blocks, list):
            raise ValueError("Targets must be lists.")
        if len(txs) + len(blocks) > MAX_TARGETS or not all(is_hash(tx) for tx in txs):
            raise ValueError("Use up to 3 targets combined and valid 32-byte transaction hashes.")
        if not all(isinstance(item, str) for item in blocks):
            raise ValueError("Block targets must be strings.")
        canonical_blocks = [block_id(item) for item in blocks]
        if not txs and not blocks:
            canonical_blocks = ["0x0"]
        self.transport, self.clock, self.monotonic, self.sleep = transport, clock, monotonic, sleep
        self.started = monotonic()
        self.head_number: int | None = None
        self.report: dict[str, Any] = {
            "schema_version": 1, "mode": "live", "endpoint": endpoint, "preset": preset,
            "started_at": timestamp(clock()), "finished_at": None, "request_count": 0,
            "limits": {"request_budget": budget, "timeout_seconds": timeout,
                       "deadline_seconds": DEADLINE_SECONDS, "max_response_bytes": MAX_RESPONSE_BYTES,
                       "max_targets": MAX_TARGETS, "tip_retries": 1},
            "stop_reason": None, "chain": {"expected": 5042, "observed": None,
                                         "verdict": "insufficient-evidence"},
            "head": empty_finding("observed-head"), "observations": [], "method_support": {},
            "transactions": [empty_finding(tx.lower()) for tx in txs],
            "blocks": [empty_finding(item) for item in canonical_blocks],
            "limits_of_evidence": [
                "Timestamped endpoint observations; not an authoritative chain source or finality proof.",
                "Null does not prove absence, failure, pruning or endpoint misconduct.",
                "Header availability at selected blocks does not establish archive-state completeness.",
                "Near-tip changes may reflect backend import lag or changing chain observations.",
                "Head age depends on local clock; this run does not measure uptime, reliability or speed.",
            ],
        }

    def near_tip(self, number: int | None) -> bool:
        return (number is not None and self.head_number is not None
                and 0 <= self.head_number - number <= 2)

    def call(self, method: str, params: list[Any], near_tip: bool = False) -> dict[str, Any]:
        for attempt in range(2 if near_tip else 1):
            remaining = DEADLINE_SECONDS - (self.monotonic() - self.started)
            if self.report["request_count"] >= self.report["limits"]["request_budget"]:
                self.report["stop_reason"] = "request-budget"
                raise StopRun
            if remaining <= 0:
                self.report["stop_reason"] = "deadline"
                raise StopRun
            self.report["request_count"] += 1
            observed_at = timestamp(self.clock())
            try:
                result = self.transport.call(method, params,
                                             min(self.report["limits"]["timeout_seconds"], remaining))
            except KeyboardInterrupt:
                self.report["observations"].append({"request": self.report["request_count"],
                    "method": method, "params": params, "observed_at": observed_at,
                    "completed_at": timestamp(self.clock()), "status": "cancelled"})
                self.report["stop_reason"] = "cancelled"
                raise StopRun from None
            self.report["observations"].append({"request": self.report["request_count"],
                "method": method, "params": params, "observed_at": observed_at,
                "completed_at": timestamp(self.clock()), "attempt": attempt + 1, **result})
            support = self.report["method_support"]
            if result["status"] == "ok":
                support[method] = "observed-supported"
            elif result.get("code") == -32601:
                support[method] = "observed-unsupported"
            else:
                support.setdefault(method, "unknown")
            if result.get("code") != -32014 or attempt == 1 or not near_tip:
                return result
            self.sleep(0.25)
        raise AssertionError("unreachable")

    def pair(self, first: dict[str, Any], expected_number: int | None = None,
             expected_hash: str | None = None) -> dict[str, Any]:
        if first.get("status") != "ok":
            return {"verdict": "insufficient-evidence", "detail": "Block query returned an error."}
        value = first.get("result")
        if value is None:
            return {"verdict": "observed-null", "detail": "Block query returned null; reason unknown."}
        if not valid_block(value):
            return {"verdict": "insufficient-evidence", "detail": "Malformed block fields."}
        number, pinned_hash = quantity(value["number"]), value["hash"].lower()
        if ((expected_number is not None and number != expected_number)
                or (expected_hash is not None and pinned_hash != expected_hash.lower())):
            return {"verdict": "inconsistent-observation", "detail": "Returned block differs from requested identifier."}
        by_hash = self.call("eth_getBlockByHash", [pinned_hash, False], self.near_tip(number))
        other = by_hash.get("result")
        if by_hash["status"] != "ok" or not valid_block(other):
            return {"verdict": "observed-null" if by_hash["status"] == "ok" and other is None
                    else "insufficient-evidence", "detail": "Pinned hash lookup unavailable or malformed."}
        matches = (other["hash"].lower() == pinned_hash and quantity(other["number"]) == number
                   and other["timestamp"] == value["timestamp"]
                   and [tx.lower() for tx in other["transactions"]]
                   == [tx.lower() for tx in value["transactions"]])
        if not matches and self.near_tip(number):
            # Repeat the same pinned number/hash, never chase 'latest'.
            repeated = self.call("eth_getBlockByNumber", [hex(number or 0), False], True)
            repeated_hash = self.call("eth_getBlockByHash", [pinned_hash, False], True)
            a, b = repeated.get("result"), repeated_hash.get("result")
            if repeated["status"] != "ok" or repeated_hash["status"] != "ok" or not valid_block(a) or not valid_block(b):
                return {"verdict": "insufficient-evidence", "detail": "Near-tip repeat was unavailable."}
            matches = (a["hash"].lower() == b["hash"].lower() == pinned_hash
                       and quantity(a["number"]) == quantity(b["number"]) == number
                       and a["timestamp"] == b["timestamp"] == value["timestamp"]
                       and a["transactions"] == b["transactions"] == value["transactions"])
        return {"verdict": "verified" if matches else "inconsistent-observation",
                "detail": "Pinned number/hash lookups agree." if matches else
                          "Pinned observations disagree, including after one near-tip repeat where applicable.",
                "number": number, "hash": pinned_hash, "timestamp": quantity(value["timestamp"])}

    def transaction(self, target: str) -> dict[str, Any]:
        finding = empty_finding(target)
        tx = self.call("eth_getTransactionByHash", [target])
        receipt = self.call("eth_getTransactionReceipt", [target])
        if tx["status"] != "ok" or receipt["status"] != "ok":
            finding["detail"] = "Transaction or receipt request errored; execution remains unknown."
            return finding
        a, b = tx.get("result"), receipt.get("result")
        if a is None or b is None:
            finding.update(verdict="observed-null", detail="Transaction or receipt was null. Pending, import lag or unavailable history are possible; absence and failure are not proven.")
            return finding
        if not isinstance(a, dict) or not isinstance(b, dict):
            return finding
        if (not is_hash(a.get("hash")) or not is_hash(b.get("transactionHash"))
                or not is_hash(b.get("blockHash")) or quantity(b.get("blockNumber")) is None
                or quantity(b.get("transactionIndex")) is None
                or b.get("status") not in ("0x0", "0x1")):
            finding["detail"] = "Malformed transaction/receipt fields or unsupported receipt status."
            return finding
        pending_keys = ("blockNumber", "blockHash", "transactionIndex")
        if all(key in a and a[key] is None for key in pending_keys):
            finding.update(verdict="inconsistent-observation", detail="Valid pending transaction observation conflicts with a valid mined receipt; sequential near-tip observations may change.")
            return finding
        if (not is_hash(a.get("blockHash")) or quantity(a.get("blockNumber")) is None
                or quantity(a.get("transactionIndex")) is None):
            finding["detail"] = "Incomplete or malformed mined/pending transaction fields."
            return finding
        number = quantity(a["blockNumber"])
        matches = (a["hash"].lower() == b["transactionHash"].lower() == target
                   and a["blockHash"].lower() == b["blockHash"].lower()
                   and quantity(a["blockNumber"]) == quantity(b["blockNumber"])
                   and quantity(a["transactionIndex"]) == quantity(b["transactionIndex"]))
        if not matches:
            finding.update(verdict="inconsistent-observation", detail="Transaction/receipt hash, block or position fields disagree. Tip/import changes are possible; no misconduct conclusion.")
            return finding
        header = self.call("eth_getBlockByNumber", [a["blockNumber"], False], self.near_tip(number))
        pinned = self.pair(header, number, a["blockHash"])
        finding.update(pinned)
        if pinned["verdict"] == "verified":
            transactions = header["result"]["transactions"]
            index = quantity(a["transactionIndex"])
            if index is None or index >= len(transactions) or transactions[index].lower() != target:
                finding.update(verdict="inconsistent-observation", detail="Pinned block does not contain requested transaction at the observed index.")
            else:
                finding["execution"] = "succeeded" if b["status"] == "0x1" else "failed"
                finding["detail"] = "Receipt, transaction and pinned block inclusion agree at observation times."
        return finding

    def execute(self) -> dict[str, Any]:
        try:
            chain = self.call("eth_chainId", [])
            observed = quantity(chain.get("result")) if chain["status"] == "ok" else None
            self.report["chain"]["observed"] = observed
            if observed != 5042:
                self.report["stop_reason"] = "chain-unverified" if observed is None else "chain-mismatch"
                if observed is not None:
                    self.report["chain"]["verdict"] = "inconsistent-observation"
                return self.report
            self.report["chain"]["verdict"] = "verified"
            head = self.call("eth_blockNumber", [])
            self.head_number = quantity(head.get("result")) if head["status"] == "ok" else None
            if self.head_number is None:
                self.report["stop_reason"] = "head-unverified"
                return self.report
            head_block = self.call("eth_getBlockByNumber", [hex(self.head_number), False], True)
            self.report["head"].update(self.pair(head_block, self.head_number))
            if self.report["head"]["verdict"] != "verified":
                self.report["stop_reason"] = "head-unverified"
                return self.report
            age = self.clock() - self.report["head"]["timestamp"]
            self.report["head"]["age_seconds_local_clock"] = round(age, 3)
            self.report["head"]["freshness"] = "future-local-clock" if age < -5 else "older-than-120s" if age > 120 else "within-120s-of-local-clock"
            for finding in self.report["transactions"]:
                finding.update(self.transaction(finding["target"]))
            for finding in self.report["blocks"]:
                target = finding["target"]
                if is_hash(target):
                    first = self.call("eth_getBlockByHash", [target, False])
                    if first["status"] == "ok" and valid_block(first.get("result")):
                        value = first["result"]
                        if value["hash"].lower() != target:
                            finding.update(verdict="inconsistent-observation", detail="Initial hash lookup returned a different block hash.")
                            continue
                        by_number = self.call("eth_getBlockByNumber", [value["number"], False], self.near_tip(quantity(value["number"])))
                        numbered = by_number.get("result")
                        if by_number["status"] == "ok" and valid_block(numbered) and (
                                numbered["hash"].lower() != target
                                or quantity(numbered["number"]) != quantity(value["number"])
                                or numbered["timestamp"] != value["timestamp"]
                                or [tx.lower() for tx in numbered["transactions"]]
                                != [tx.lower() for tx in value["transactions"]]):
                            finding.update(verdict="inconsistent-observation", detail="Initial pinned-hash and number observations disagree; neither is discarded.")
                            continue
                        finding.update(self.pair(by_number, quantity(value["number"]), target))
                    else:
                        finding.update(self.pair(first, expected_hash=target))
                else:
                    number = quantity(target)
                    first = self.call("eth_getBlockByNumber", [target, False], self.near_tip(number))
                    finding.update(self.pair(first, number))
        except StopRun:
            pass
        except KeyboardInterrupt:
            self.report["stop_reason"] = "cancelled"
        finally:
            self.report["finished_at"] = timestamp(self.clock())
        return self.report


def run(options: dict[str, Any], transport: Transport, *, clock: Callable[[], float] = time.time,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    return Runner(options, transport, clock, monotonic, sleep).execute()
