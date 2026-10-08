from copy import deepcopy
from typing import Any

TX = "0x" + "1" * 64
HEAD_HASH = "0x" + "a" * 64
OLD_HASH = "0x" + "b" * 64
NOW = 1700000005.0


def block(number: str = "0x64", block_hash: str = HEAD_HASH) -> dict[str, Any]:
    return {"number": number, "hash": block_hash, "timestamp": "0x6553f100",
            "transactions": [TX] if number == "0x64" else []}


class FixtureTransport:
    def __init__(self, overrides: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.overrides = deepcopy(overrides or {})
        self.calls: list[tuple[str, list[Any]]] = []

    def call(self, method: str, params: list[Any], timeout: float) -> dict[str, Any]:
        self.calls.append((method, params))
        if self.overrides.get(method):
            return self.overrides[method].pop(0)
        if method == "eth_chainId":
            value: Any = "0x13b2"
        elif method == "eth_blockNumber":
            value = "0x64"
        elif method == "eth_getBlockByNumber":
            value = block() if params[0] == "0x64" else block(params[0], OLD_HASH)
        elif method == "eth_getBlockByHash":
            value = block() if params[0] == HEAD_HASH else block("0x0", OLD_HASH)
        elif method == "eth_getTransactionByHash":
            value = {"hash": TX, "blockNumber": "0x64", "blockHash": HEAD_HASH,
                     "transactionIndex": "0x0"}
        elif method == "eth_getTransactionReceipt":
            value = {"transactionHash": TX, "blockNumber": "0x64", "blockHash": HEAD_HASH,
                     "transactionIndex": "0x0", "status": "0x1"}
        else:
            return {"status": "rpc-error", "code": -32601}
        return {"status": "ok", "result": value}
