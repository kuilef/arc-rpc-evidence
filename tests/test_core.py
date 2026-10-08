import unittest
from typing import Any

from arc_rpc_evidence.core import run
from tests.helpers import HEAD_HASH, NOW, OLD_HASH, TX, FixtureTransport, block


class EvidenceTests(unittest.TestCase):
    def check(self, overrides: dict[str, list[dict[str, Any]]] | None = None,
              **options: Any) -> tuple[dict[str, Any], FixtureTransport]:
        transport = FixtureTransport(overrides)
        report = run({"preset": "mainnet", "transactions": [TX], "blocks": [],
                      **options}, transport, clock=lambda: NOW, sleep=lambda seconds: None)
        return report, transport

    def test_matching_receipt_and_pinned_inclusion_are_verified(self) -> None:
        report, _ = self.check()
        self.assertEqual(report.get("transactions", [{}])[0].get("verdict"), "verified")

    def test_wrong_chain_stops_after_one_request(self) -> None:
        report, transport = self.check({"eth_chainId": [{"status": "ok", "result": "0x1"}]})
        self.assertEqual(report.get("stop_reason"), "chain-mismatch")
        self.assertEqual(len(transport.calls), 1)

    def test_null_transaction_is_unknown_not_missing_or_failed(self) -> None:
        report, _ = self.check({"eth_getTransactionByHash": [{"status": "ok", "result": None}]})
        self.assertEqual(report.get("transactions", [{}])[0].get("verdict"), "observed-null")
        self.assertEqual(report.get("transactions", [{}])[0].get("execution"), "unknown")

    def test_null_receipt_is_unknown(self) -> None:
        report, _ = self.check({"eth_getTransactionReceipt": [{"status": "ok", "result": None}]})
        self.assertEqual(report.get("transactions", [{}])[0].get("verdict"), "observed-null")

    def test_failed_receipt_remains_verified_inclusion_with_failed_execution(self) -> None:
        receipt = {"transactionHash": TX, "blockNumber": "0x64", "blockHash": HEAD_HASH,
                   "transactionIndex": "0x0", "status": "0x0"}
        report, _ = self.check({"eth_getTransactionReceipt": [{"status": "ok", "result": receipt}]})
        self.assertEqual(report.get("transactions", [{}])[0].get("execution"), "failed")
        self.assertEqual(report.get("transactions", [{}])[0].get("verdict"), "verified")

    def test_missing_historical_block_is_observed_null(self) -> None:
        report, _ = self.check({"eth_getBlockByNumber": [{"status": "ok", "result": block()},
                                                        {"status": "ok", "result": None}]},
                               transactions=[], blocks=["0"])
        self.assertEqual(report.get("blocks", [{}])[0].get("verdict"), "observed-null")

    def test_persistent_block_hash_conflict_is_inconsistent_observation(self) -> None:
        report, _ = self.check({"eth_getBlockByHash": [{"status": "ok", "result": block("0x64", OLD_HASH)}] * 5})
        self.assertEqual(report.get("head", {}).get("verdict"), "inconsistent-observation")

    def test_transient_tip_error_retries_once_and_recovers(self) -> None:
        report, transport = self.check({"eth_getBlockByNumber": [{"status": "rpc-error", "code": -32014}]})
        self.assertEqual(report.get("head", {}).get("verdict"), "verified")
        self.assertEqual(sum(method == "eth_getBlockByNumber" and params[0] == "0x64"
                             for method, params in transport.calls), 3)

    def test_transient_tip_error_stops_after_one_retry(self) -> None:
        report, transport = self.check({"eth_getBlockByNumber": [{"status": "rpc-error", "code": -32014}] * 10})
        self.assertEqual(report.get("head", {}).get("verdict"), "insufficient-evidence")
        self.assertLessEqual(len(transport.calls), 8)

    def test_old_block_tip_error_is_not_retried(self) -> None:
        report, transport = self.check({"eth_getBlockByNumber": [{"status": "ok", "result": block()},
                                        {"status": "rpc-error", "code": -32014}]},
                                       transactions=[], blocks=["0"])
        self.assertEqual(report.get("blocks", [{}])[0].get("verdict"), "insufficient-evidence")
        self.assertEqual(sum(params[0] == "0x0" for method, params in transport.calls
                             if method == "eth_getBlockByNumber"), 1)

    def test_rate_limit_and_timeout_preserve_unknown(self) -> None:
        for status in ("rate-limit", "timeout", "malformed", "rpc-error"):
            with self.subTest(status=status):
                report, _ = self.check({"eth_getTransactionReceipt": [{"status": status, "code": -32601}]})
                self.assertEqual(report.get("transactions", [{}])[0].get("verdict"), "insufficient-evidence")

    def test_malformed_quantity_cannot_verify_chain(self) -> None:
        report, transport = self.check({"eth_chainId": [{"status": "ok", "result": "0x013b2"}]})
        self.assertEqual(report.get("stop_reason"), "chain-unverified")
        self.assertEqual(len(transport.calls), 1)

    def test_invalid_receipt_status_is_insufficient(self) -> None:
        report, _ = self.check({"eth_getTransactionReceipt": [{"status": "ok", "result": {"status": "0x2"}}]})
        self.assertEqual(report.get("transactions", [{}])[0].get("verdict"), "insufficient-evidence")

    def test_maximum_requests_is_enforced(self) -> None:
        report, transport = self.check(budget=2)
        self.assertEqual(report.get("stop_reason"), "request-budget")
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(report.get("request_count"), 2)

    def test_observation_timestamps_and_method_support_are_recorded(self) -> None:
        report, transport = self.check()
        self.assertEqual(report.get("request_count"), len(transport.calls))
        self.assertEqual(len(report.get("observations", [])), len(transport.calls))
        self.assertTrue(all("observed_at" in entry for entry in report.get("observations", [])))
        self.assertEqual(report.get("method_support", {}).get("eth_chainId"), "observed-supported")

    def test_pending_transaction_with_null_receipt_is_unknown(self) -> None:
        pending = {"hash": TX, "blockNumber": None, "blockHash": None, "transactionIndex": None}
        report, _ = self.check({"eth_getTransactionByHash": [{"status": "ok", "result": pending}],
                               "eth_getTransactionReceipt": [{"status": "ok", "result": None}]})
        self.assertEqual(report.get("transactions", [{}])[0].get("execution"), "unknown")

    def test_empty_or_incomplete_objects_are_insufficient_not_pending_conflict(self) -> None:
        mined_tx = {"hash": TX, "blockNumber": "0x64", "blockHash": HEAD_HASH,
                    "transactionIndex": "0x0"}
        mined_receipt = {"transactionHash": TX, "blockNumber": "0x64", "blockHash": HEAD_HASH,
                         "transactionIndex": "0x0", "status": "0x1"}
        pending = {"hash": TX, "blockNumber": None, "blockHash": None, "transactionIndex": None}
        partial_pending = {"hash": TX, "blockNumber": None, "blockHash": None}
        partial_receipt = {key: value for key, value in mined_receipt.items() if key != "status"}
        for tx, receipt in (({}, {}), ({}, mined_receipt), ({"hash": TX}, mined_receipt),
                            (partial_pending, mined_receipt), (pending, {}),
                            (pending, partial_receipt), (mined_tx, {"transactionHash": TX})):
            with self.subTest(tx=tx, receipt=receipt):
                report, _ = self.check({"eth_getTransactionByHash": [{"status": "ok", "result": tx}],
                                       "eth_getTransactionReceipt": [{"status": "ok", "result": receipt}]})
                self.assertEqual(report["transactions"][0]["verdict"], "insufficient-evidence")
                self.assertEqual(report["transactions"][0]["execution"], "unknown")

    def test_valid_pending_and_valid_mined_receipt_conflict_is_inconsistent(self) -> None:
        pending = {"hash": TX, "blockNumber": None, "blockHash": None, "transactionIndex": None}
        receipt = {"transactionHash": TX, "blockNumber": "0x64", "blockHash": HEAD_HASH,
                   "transactionIndex": "0x0", "status": "0x1"}
        report, _ = self.check({"eth_getTransactionByHash": [{"status": "ok", "result": pending}],
                               "eth_getTransactionReceipt": [{"status": "ok", "result": receipt}]})
        self.assertEqual(report["transactions"][0]["verdict"], "inconsistent-observation")
        self.assertEqual(report["transactions"][0]["execution"], "unknown")

    def test_invalid_inputs_make_no_requests(self) -> None:
        for options in ({"preset": "http://127.0.0.1"}, {"budget": 25},
                        {"transactions": ["bad"]}, {"blocks": ["../file"]},
                        {"transactions": [TX] * 4}, {"timeout": 0}):
            with self.subTest(options=options):
                transport = FixtureTransport()
                with self.assertRaises(ValueError):
                    run({"preset": "mainnet", **options}, transport)
                self.assertEqual(transport.calls, [])

    def test_ctrl_c_keeps_partial_attempt_accounting(self) -> None:
        class CancelTransport(FixtureTransport):
            def call(self, method: str, params: list[Any], timeout: float) -> dict[str, Any]:
                raise KeyboardInterrupt
        report = run({"preset": "mainnet"}, CancelTransport(), clock=lambda: NOW)
        self.assertEqual(report.get("stop_reason"), "cancelled")
        self.assertEqual(report.get("request_count"), 1)

    def test_malformed_block_hash_cannot_be_verified(self) -> None:
        malformed = block()
        malformed["hash"] = "bad"
        report, _ = self.check({"eth_getBlockByNumber": [{"status": "ok", "result": malformed}]})
        self.assertEqual(report.get("head", {}).get("verdict"), "insufficient-evidence")

    def test_deadline_stops_before_new_http_attempt(self) -> None:
        moments = iter([0.0, 46.0])
        transport = FixtureTransport()
        report = run({"preset": "mainnet"}, transport, monotonic=lambda: next(moments))
        self.assertEqual(report["stop_reason"], "deadline")
        self.assertEqual(report["request_count"], 0)
        self.assertEqual(transport.calls, [])

    def test_wrong_transaction_hash_cannot_be_verified(self) -> None:
        report, _ = self.check({"eth_getTransactionByHash": [{"status": "ok", "result": {
            "hash": OLD_HASH, "blockNumber": "0x64", "blockHash": HEAD_HASH,
            "transactionIndex": "0x0"}}]})
        self.assertEqual(report["transactions"][0]["verdict"], "inconsistent-observation")

    def test_wrong_inclusion_index_cannot_be_verified(self) -> None:
        no_tx = block()
        no_tx["transactions"] = []
        report, _ = self.check({"eth_getBlockByNumber": [{"status": "ok", "result": no_tx}] * 5,
                               "eth_getBlockByHash": [{"status": "ok", "result": no_tx}] * 5})
        self.assertEqual(report["transactions"][0]["verdict"], "inconsistent-observation")

    def test_wrong_hash_from_first_target_lookup_cannot_be_hidden(self) -> None:
        report, _ = self.check({"eth_getBlockByHash": [{"status": "ok", "result": block()},
                                                       {"status": "ok", "result": block("0x0", HEAD_HASH)}]},
                               transactions=[], blocks=[OLD_HASH])
        self.assertEqual(report["blocks"][0]["verdict"], "inconsistent-observation")

    def test_initial_hash_lookup_conflicting_fields_are_retained(self) -> None:
        for field, value in (("timestamp", "0x1"), ("transactions", [TX])):
            with self.subTest(field=field):
                initial = block("0x0", OLD_HASH)
                initial[field] = value
                report, _ = self.check({"eth_getBlockByHash": [{"status": "ok", "result": block()},
                                                               {"status": "ok", "result": initial}]},
                                       transactions=[], blocks=[OLD_HASH])
                self.assertEqual(report["blocks"][0]["verdict"], "inconsistent-observation")

    def test_unsupported_method_is_observed_without_retry(self) -> None:
        report, transport = self.check({"eth_getTransactionReceipt": [{"status": "rpc-error", "code": -32601}]})
        self.assertEqual(report["method_support"]["eth_getTransactionReceipt"], "observed-unsupported")
        self.assertEqual(sum(method == "eth_getTransactionReceipt" for method, _ in transport.calls), 1)


if __name__ == "__main__":
    unittest.main()
