from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request

from src.config.settings import get_logger, get_settings
from src.processing.pipeline import ingest_text_content

app = Flask(__name__)
logger = get_logger("voice_ingestor")


def transcribe_audio(path: str | Path, language: str = "it") -> str:
    settings = get_settings()
    from faster_whisper import WhisperModel

    model = WhisperModel(settings.whisper_model)
    segments, _ = model.transcribe(str(path), language=language)
    return " ".join(segment.text.strip() for segment in segments if segment.text.strip())


def ingest_voice_file(path: str | Path, forced_scope: str | None = None) -> Path:
    transcript = transcribe_audio(path)
    result = ingest_text_content(text=transcript, source="voice", forced_scope=forced_scope)
    return result.path


@app.post("/voice")
def voice_webhook():
    if "file" not in request.files:
        return jsonify({"error": "missing file"}), 400
    upload = request.files["file"]
    suffix = Path(upload.filename or "audio.m4a").suffix or ".m4a"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        upload.save(temp_file.name)
        path = ingest_voice_file(temp_file.name, forced_scope=request.args.get("scope"))
    return jsonify({"path": str(path)})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest a voice note")
    parser.add_argument("audio_path")
    parser.add_argument("--scope", choices=["work", "personal"], default=None)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.serve:
        app.run(host=args.host, port=args.port)
        return 0
    path = ingest_voice_file(args.audio_path, forced_scope=args.scope)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
