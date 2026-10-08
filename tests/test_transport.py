import io
import json
import unittest
from http.client import IncompleteRead, RemoteDisconnected
from typing import Any
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from arc_rpc_evidence.core import run
from arc_rpc_evidence.transport import HttpTransport, parse_payload


class TransportTests(unittest.TestCase):
    def test_result_and_null_have_observed_support(self) -> None:
        for value in (None, "0x13b2", {}):
            payload = json.dumps({"jsonrpc": "2.0", "id": 1, "result": value}).encode()
            self.assertEqual(parse_payload(payload, 1).get("status"), "ok")

    def test_malformed_envelopes_are_rejected(self) -> None:
        for payload in (b"not json", b"[]", b'{"id":1,"result":0}',
                        b'{"jsonrpc":"2.0","id":2,"result":0}',
                        b'{"jsonrpc":"2.0","id":1,"result":null,"error":{}}',
                        b'{"jsonrpc":"2.0","id":1,"error":{"code":true}}',
                        b'{"jsonrpc":"2.0","id":1,"id":2,"result":0}',
                        b'{"jsonrpc":"2.0","id":1,"result":NaN}'):
            with self.subTest(payload=payload):
                self.assertEqual(parse_payload(payload, 1).get("status"), "malformed")

    def test_overflow_float_is_malformed_before_report_export(self) -> None:
        for number in ("1e999", "-1e999"):
            payload = ('{"jsonrpc":"2.0","id":1,"result":{"nested":[{"value":' + number + '}]}}').encode()
            self.assertEqual(parse_payload(payload, 1).get("status"), "malformed")

    def test_truncated_http_response_preserves_error_outcome(self) -> None:
        for error in (IncompleteRead(b"partial", 100), RemoteDisconnected("private")):
            with self.subTest(error=type(error).__name__), patch("urllib.request.OpenerDirector.open", side_effect=error):
                self.assertEqual(HttpTransport().call("eth_chainId", [], 1).get("status"), "protocol-error")

    def test_truncated_body_retains_prior_chain_observation_and_exact_count(self) -> None:
        class TruncatedResponse(io.BytesIO):
            def read1(self, size: int = -1) -> bytes:
                raise IncompleteRead(b"partial", 10)
        responses = [io.BytesIO(b'{"jsonrpc":"2.0","id":1,"result":"0x13b2"}'), TruncatedResponse()]
        with patch("urllib.request.OpenerDirector.open", side_effect=responses):
            report = run({"preset": "mainnet"}, HttpTransport())
        self.assertEqual(report["request_count"], 2)
        self.assertEqual(report["chain"]["verdict"], "verified")
        self.assertEqual(report["observations"][1]["status"], "protocol-error")

    def test_documented_large_log_range_error_is_offline_only(self) -> None:
        payload = b'{"jsonrpc":"2.0","id":1,"error":{"code":-32012,"message":"range"}}'
        self.assertEqual(parse_payload(payload, 1).get("code"), -32012)
        self.assertEqual(parse_payload(payload, 1).get("status"), "rpc-error")

    def test_endpoint_restrictions_reject_credentials_private_urls_and_files(self) -> None:
        for preset in ("https://rpc.mainnet.arc.io?key=secret", "https://user:pass@rpc.mainnet.arc.io",
                       "http://127.0.0.1:8545", "http://169.254.169.254", "file:///etc/passwd",
                       "https://rpc.mainnet.arc.io/", "https://example.org", "testnet"):
            with self.subTest(preset=preset), self.assertRaises(ValueError):
                HttpTransport(preset)

    def test_write_methods_and_arbitrary_params_are_rejected_before_network(self) -> None:
        transport = HttpTransport()
        for method, params in (("eth_sendRawTransaction", ["0x00"]),
                               ("eth_getLogs", [{"fromBlock": "0x0", "toBlock": "0xffffff"}]),
                               ("eth_getBlockByNumber", ["latest", True]),
                               ("eth_chainId", ["extra"])):
            with self.subTest(method=method), self.assertRaises(ValueError):
                transport.call(method, params, 1)

    def test_http_errors_and_timeouts_are_bounded_and_sanitized(self) -> None:
        for error, expected in ((HTTPError("https://rpc.mainnet.arc.io", 429, "private", {}, None), "rate-limit"),
                                (HTTPError("https://rpc.mainnet.arc.io", 302, "redirect", {}, None), "redirect-rejected"),
                                (URLError("credential"), "network-error"), (TimeoutError(), "timeout")):
            with self.subTest(expected=expected), patch("urllib.request.OpenerDirector.open", side_effect=error):
                result = HttpTransport().call("eth_chainId", [], 1)
                self.assertEqual(result.get("status"), expected)
                self.assertNotIn("credential", str(result))

    def test_response_size_is_capped(self) -> None:
        class Response(io.BytesIO):
            status = 200
        with patch("urllib.request.OpenerDirector.open", return_value=Response(b"x" * 262145)):
            self.assertEqual(HttpTransport().call("eth_chainId", [], 1).get("status"), "response-too-large")

    def test_request_uses_official_url_and_no_proxy(self) -> None:
        requests: list[Any] = []
        def opened(request: Any, timeout: float) -> io.BytesIO:
            requests.append(request)
            return io.BytesIO(b'{"jsonrpc":"2.0","id":1,"result":"0x13b2"}')
        with patch("urllib.request.OpenerDirector.open", side_effect=opened):
            self.assertEqual(HttpTransport().call("eth_chainId", [], 1).get("status"), "ok")
        self.assertEqual(requests[0].full_url, "https://rpc.mainnet.arc.io")
        self.assertEqual(requests[0].get_method(), "POST")


if __name__ == "__main__":
    unittest.main()
