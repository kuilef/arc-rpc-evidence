import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .core import run
from .demo import SCENARIOS, demo_report
from .report import markdown
from .transport import HttpTransport


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Explain bounded Arc RPC observations, with offline replay.")
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("demo", "check"):
        command = commands.add_parser(name, description="Maximum 24 attempts, 3 targets, 5s socket timeout; no URL input.")
        command.add_argument("--budget", type=int, default=24, help="Maximum attempts including retries (1..24)")
        command.add_argument("--timeout", type=float, default=5, help="Socket timeout in seconds (>0..5)")
        command.add_argument("--output", type=Path, help="Export directory for report.json and report.md; never overwrite")
        if name == "demo":
            command.add_argument("--scenario", choices=SCENARIOS, default="healthy")
        else:
            command.add_argument("--preset", choices=("mainnet",), default="mainnet", help="Official anonymous Arc mainnet RPC")
            command.add_argument("--tx", action="append", default=[], help="Transaction hash, repeat up to 3 targets combined")
            command.add_argument("--block", action="append", default=[], help="Block number or hash; default: genesis header")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            if any((args.output / name).exists() for name in ("report.json", "report.md")):
                raise ValueError("Export file already exists; select a new output directory.")
        if args.command == "demo":
            report = demo_report(args.scenario, args.budget, args.timeout)
        else:
            report = run({"preset": args.preset, "transactions": args.tx, "blocks": args.block,
                          "budget": args.budget, "timeout": args.timeout}, HttpTransport(args.preset))
        readable = markdown(report)
        if args.output:
            with (args.output / "report.json").open("x", encoding="utf-8") as destination:
                destination.write(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + "\n")
            with (args.output / "report.md").open("x", encoding="utf-8") as destination:
                destination.write(readable)
        print(readable)
        return 130 if report["stop_reason"] == "cancelled" else 0
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
