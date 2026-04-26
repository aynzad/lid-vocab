import argparse
from pathlib import Path
import sys

from leben_vocab.export import export_vocabulary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lid-vocab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--state", default="Berlin")
    export_parser.add_argument("--target-lang", required=True)
    export_parser.add_argument("--output", required=True, type=Path)

    args = parser.parse_args(argv)
    if args.command == "export":
        export_vocabulary(
            state=args.state,
            target_languages=_target_languages(args.target_lang),
            output_path=_dist_output_path(args.output),
            progress=_print_progress,
        )
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _dist_output_path(output_path: Path) -> Path:
    if output_path.is_absolute() or output_path.parts[:1] == ("dist",):
        return output_path
    return Path("dist") / output_path


def _target_languages(value: str) -> list[str]:
    languages = [language.strip() for language in value.split(",")]
    return [language for language in languages if language]


def _print_progress(message: str) -> None:
    print(f"[lid-vocab] {message}", file=sys.stderr, flush=True)
