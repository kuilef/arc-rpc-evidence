import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from arc_rpc_evidence.cli import main


class CliTests(unittest.TestCase):
    def test_demo_never_constructs_network_transport(self) -> None:
        output = io.StringIO()
        with patch("arc_rpc_evidence.transport.HttpTransport.call", side_effect=AssertionError("network forbidden")), contextlib.redirect_stdout(output):
            self.assertEqual(main(["demo"]), 0)
        self.assertIn("synthetic", output.getvalue())
        self.assertIn("verified", output.getvalue())
        self.assertIn("24", output.getvalue())

    def test_json_and_markdown_export_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            path = Path(directory) / "demo"
            self.assertEqual(main(["demo", "--scenario", "null-receipt", "--output", str(path)]), 0)
            self.assertTrue((path / "report.json").exists())
            self.assertTrue((path / "report.md").exists())
            report = json.loads((path / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "synthetic")
            self.assertEqual(report["transactions"][0]["verdict"], "observed-null")
            self.assertIn("unknown", (path / "report.md").read_text(encoding="utf-8"))

    def test_exports_never_overwrite_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "report.json").write_text("keep", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["demo", "--output", directory]), 2)
            self.assertEqual((path / "report.json").read_text(encoding="utf-8"), "keep")

    def test_invalid_target_does_not_start_network(self) -> None:
        with patch("arc_rpc_evidence.transport.HttpTransport.call", side_effect=AssertionError("network forbidden")), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["check", "--tx", "invalid"]), 2)

    def test_budget_stop_is_visible_in_report(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["demo", "--budget", "1"]), 0)
        self.assertIn("request-budget", output.getvalue())
        self.assertIn("insufficient-evidence", output.getvalue())

    def test_help_lists_limits_and_no_url_flag(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as error:
            main(["check", "--help"])
        self.assertEqual(error.exception.code, 0)
        self.assertIn("24", output.getvalue())
        self.assertNotIn("--url", output.getvalue())

    def test_overflow_response_still_exports_complete_malformed_report(self) -> None:
        response = io.BytesIO(b'{"jsonrpc":"2.0","id":1,"result":{"value":1e999}}')
        with tempfile.TemporaryDirectory() as directory, patch("urllib.request.OpenerDirector.open", return_value=response), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["check", "--output", directory]), 0)
            report = json.loads((Path(directory) / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["observations"][0]["status"], "malformed")
            self.assertEqual(report["request_count"], 1)


if __name__ == "__main__":
    unittest.main()
