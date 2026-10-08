"""Synthetic replay scenarios. No sockets, accounts, wallets or external files."""
from copy import deepcopy
from typing import Any

from .core import run

TX = "0x" + "1" * 64
HEAD_HASH = "0x" + "a" * 64
OLD_HASH = "0x" + "b" * 64
DEMO_TIME = 1791417605.0
SCENARIOS = ("healthy", "null-receipt", "null-transaction", "failed-receipt", "missing-block",
             "conflict", "tip-recover", "tip-stop", "rate-limit", "timeout", "malformed", "wrong-chain")


def demo_block(number: str = "0x64", block_hash: str = HEAD_HASH) -> dict[str, Any]:
    return {"number": number, "hash": block_hash, "timestamp": hex(int(DEMO_TIME) - 5),
            "transactions": [TX] if number == "0x64" else []}


class DemoTransport:
    def __init__(self, scenario: str) -> None:
        if scenario not in SCENARIOS:
            raise ValueError("Unknown demo scenario")
        self.scenario = scenario
        self.number_calls = 0

    def call(self, method: str, params: list[Any], timeout: float) -> dict[str, Any]:
        if method == "eth_chainId":
            value: Any = "0x1" if self.scenario == "wrong-chain" else "0x13b2"
        elif method == "eth_blockNumber":
            value = "0x64"
        elif method == "eth_getBlockByNumber":
            self.number_calls += 1
            if self.scenario in ("tip-recover", "tip-stop") and (self.number_calls == 1 or self.scenario == "tip-stop"):
                return {"status": "rpc-error", "code": -32014}
            if self.scenario == "missing-block" and params[0] == "0x0":
                value = None
            else:
                value = demo_block() if params[0] == "0x64" else demo_block(params[0], OLD_HASH)
        elif method == "eth_getBlockByHash":
            value = demo_block() if params[0] == HEAD_HASH else demo_block("0x0", OLD_HASH)
            if self.scenario == "conflict":
                value["hash"] = OLD_HASH
        elif method == "eth_getTransactionByHash":
            value = None if self.scenario == "null-transaction" else {
                "hash": TX, "blockNumber": "0x64", "blockHash": HEAD_HASH, "transactionIndex": "0x0"}
        elif method == "eth_getTransactionReceipt":
            if self.scenario in ("rate-limit", "timeout", "malformed"):
                return {"status": self.scenario}
            value = None if self.scenario == "null-receipt" else {
                "transactionHash": TX, "blockNumber": "0x64", "blockHash": HEAD_HASH,
                "transactionIndex": "0x0", "status": "0x0" if self.scenario == "failed-receipt" else "0x1"}
        else:
            return {"status": "rpc-error", "code": -32601}
        return {"status": "ok", "result": deepcopy(value)}


def demo_report(scenario: str, budget: int = 24, timeout: float = 5) -> dict[str, Any]:
    report = run({"preset": "mainnet", "budget": budget, "timeout": timeout,
                  "transactions": [] if scenario == "missing-block" else [TX],
                  "blocks": ["0"] if scenario == "missing-block" else []}, DemoTransport(scenario),
                 clock=lambda: DEMO_TIME, sleep=lambda seconds: None)
    report.update(mode="synthetic", scenario=scenario,
                  endpoint="offline fixture (official mainnet preset label; zero HTTP requests)")
    report["http_request_count"] = 0
    report["simulated_request_count"] = report["request_count"]
    return report
