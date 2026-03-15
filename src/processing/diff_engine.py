from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from src.config.settings import load_prompt
from src.processing.file_readers import read_excel, read_file_to_text
from src.processing.openrouter_client import call_openrouter


def diff_excel_files(current_path: str | Path, previous_path: str | Path) -> str:
    current = read_excel(current_path)
    previous = read_excel(previous_path)
    current_tables = {table['sheet']: table['rows'] for table in current['tables']}
    previous_tables = {table['sheet']: table['rows'] for table in previous['tables']}
    lines: list[str] = []
    for sheet_name in sorted(set(current_tables) | set(previous_tables)):
        old_rows = previous_tables.get(sheet_name, [])
        new_rows = current_tables.get(sheet_name, [])
        if sheet_name not in previous_tables:
            lines.append(f"## New sheet: {sheet_name}")
        elif sheet_name not in current_tables:
            lines.append(f"## Removed sheet: {sheet_name}")
        diff = difflib.unified_diff(old_rows, new_rows, fromfile=f"old:{sheet_name}", tofile=f"new:{sheet_name}", lineterm="")
        lines.extend(diff)
    return "\n".join(lines)


def diff_documents(current_path: str | Path, previous_path: str | Path) -> str:
    current = read_file_to_text(current_path)
    previous = read_file_to_text(previous_path)
    diff = difflib.unified_diff(
        previous["text"].splitlines(),
        current["text"].splitlines(),
        fromfile=str(previous_path),
        tofile=str(current_path),
        lineterm="",
    )
    return "\n".join(diff)


def summarize_diff(diff_text: str, prompt_name: str) -> str:
    prompt = load_prompt(prompt_name).format(diff_text=diff_text[:12000])
    response = call_openrouter(prompt)
    if response:
        return response
    return diff_text[:4000]


def generate_diff_summary(current_path: str | Path, previous_path: str | Path) -> dict[str, Any]:
    current_suffix = Path(current_path).suffix.lower()
    if current_suffix in {".xlsx", ".xls", ".xlsm", ".xltx", ".xltm"}:
        raw_diff = diff_excel_files(current_path, previous_path)
        summary = summarize_diff(raw_diff, "diff_excel.txt")
    else:
        raw_diff = diff_documents(current_path, previous_path)
        summary = summarize_diff(raw_diff, "diff_document.txt")
    return {"raw_diff": raw_diff, "summary": summary}
