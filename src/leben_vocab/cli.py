import argparse
from pathlib import Path

from leben_vocab.export import export_fixture_vocabulary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="leben-vocab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--state", default="Berlin")
    export_parser.add_argument("--target-lang", required=True)
    export_parser.add_argument("--output", required=True, type=Path)

    args = parser.parse_args(argv)
    if args.command == "export":
        export_fixture_vocabulary(
            state=args.state,
            target_language=args.target_lang,
            output_path=args.output,
        )
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2
