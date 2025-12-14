"""Command-line interface for converting roster images to ICS files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .ics import DEFAULT_LOCAL_TZ, json_to_ics
from .ocr import CallUsage, RosterParseResult, RosterParser


def roster_image_to_ics(
    image_path: Path,
    *,
    ics_output: Path,
    json_output: Optional[Path] = None,
    calendar_name: str = "Roster",
    local_tz: str = DEFAULT_LOCAL_TZ,
) -> tuple[Path, RosterParseResult]:
    """Run the full pipeline: JPG -> OCR -> JSON -> ICS."""
    parser = RosterParser()
    result = parser.parse_image(image_path)
    roster_json = result.data

    if json_output:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(
            json.dumps(roster_json, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )

    ics_content = json_to_ics(roster_json, calendar_name=calendar_name, local_tz=local_tz)
    ics_output.parent.mkdir(parents=True, exist_ok=True)
    ics_output.write_text(ics_content, encoding="utf-8", newline="\n")
    return ics_output, result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert an airline roster JPG into an ICS calendar file.",
    )
    parser.add_argument("image", type=Path, help="Path to a roster image (jpg/jpeg/png).")
    parser.add_argument(
        "-o",
        "--ics-output",
        type=Path,
        help="Where to write the resulting .ics file (defaults to <image>.ics).",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path to save the intermediate roster JSON.",
    )
    parser.add_argument(
        "--calendar-name",
        default="Roster",
        help="ICS PRODID/summary prefix.",
    )
    parser.add_argument(
        "--local-tz",
        default=DEFAULT_LOCAL_TZ,
        help=f"Local timezone used for human-readable descriptions (default: {DEFAULT_LOCAL_TZ}).",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    image_path: Path = args.image
    if not image_path.exists():
        parser.error(f"Image not found: {image_path}")

    ics_output = args.ics_output or image_path.with_suffix(".ics")

    ics_path, result = roster_image_to_ics(
        image_path,
        ics_output=ics_output,
        json_output=args.json_output,
        calendar_name=args.calendar_name,
        local_tz=args.local_tz,
    )
    print(f"ICS saved to: {ics_path}")

    def fmt_usage(label: str, usage: CallUsage) -> str:
        cached_flag = "cached" if usage.cached_input_tokens else "normal"
        return (
            f"{label}: input={usage.input_tokens} (cached={usage.cached_input_tokens}, {cached_flag}), "
            f"output={usage.output_tokens}, total={usage.effective_total}"
        )

    print("OpenAI token usage:")
    print(f"- {fmt_usage('OCR', result.ocr_usage)}")
    print(f"- {fmt_usage('Parse', result.parse_usage)}")


if __name__ == "__main__":
    main()
