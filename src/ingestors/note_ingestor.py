from __future__ import annotations

import argparse
import sys

from src.processing.pipeline import ingest_text_content


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nota", description="Ingest a note into Open Memory")
    parser.add_argument("text", nargs="+", help="Text of the note")
    parser.add_argument("--personal", action="store_true", help="Shortcut for --scope personal")
    parser.add_argument("--scope", choices=["work", "personal"], default=None)
    parser.add_argument("--type", dest="item_type", default=None)
    parser.add_argument("--source", default="cli")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    text = " ".join(args.text).strip()
    forced_scope = "personal" if args.personal else args.scope
    result = ingest_text_content(
        text=text,
        source=args.source,
        prompt_name="classify_note.txt",
        forced_scope=forced_scope,
        forced_type=args.item_type,
    )
    if result.created:
        print(result.path)
    else:
        print(f"duplicate:{result.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
