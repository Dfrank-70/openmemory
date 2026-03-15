from __future__ import annotations

import email
import hashlib
import imaplib
import sys
import tempfile
import time
from email.header import decode_header
from email.message import Message
from pathlib import Path

from src.config.settings import get_logger, get_settings, slugify
from src.processing.diff_engine import generate_diff_summary
from src.processing.file_readers import read_file_to_text
from src.processing.pipeline import ingest_text_content

logger = get_logger("imap_watcher")


def _decode_value(value: str | None) -> str:
    if not value:
        return ""
    decoded_parts = decode_header(value)
    parts: list[str] = []
    for chunk, encoding in decoded_parts:
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(encoding or "utf-8", errors="ignore"))
        else:
            parts.append(chunk)
    return "".join(parts)


def _text_body(message: Message) -> str:
    if message.is_multipart():
        parts: list[str] = []
        for part in message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True) or b""
                parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="ignore"))
        return "\n".join(parts)
    payload = message.get_payload(decode=True) or b""
    return payload.decode(message.get_content_charset() or "utf-8", errors="ignore")


def _attachment_bytes(part: Message) -> tuple[str, bytes] | None:
    filename = _decode_value(part.get_filename())
    if not filename:
        return None
    payload = part.get_payload(decode=True)
    if payload is None:
        return None
    return filename, payload


def _store_attachment(filename: str, payload: bytes) -> Path:
    settings = get_settings()
    target = settings.attachments_dir / filename
    if target.exists():
        digest = hashlib.sha256(payload).hexdigest()[:8]
        target = settings.attachments_dir / f"{target.stem}-{digest}{target.suffix}"
    target.write_bytes(payload)
    return target


def _latest_matching_attachment(stem: str, suffix: str, exclude: Path | None = None) -> Path | None:
    settings = get_settings()
    matches = sorted(settings.attachments_dir.glob(f"{slugify(stem)}*{suffix}"))
    filtered = [path for path in matches if exclude is None or path != exclude]
    return filtered[-1] if filtered else None


def _normalize_attachment_name(filename: str) -> tuple[str, str]:
    path = Path(filename)
    return slugify(path.stem), path.suffix.lower()


def process_unseen_messages() -> int:
    settings = get_settings()
    mail = imaplib.IMAP4_SSL(settings.imap_host)
    mail.login(settings.imap_user, settings.imap_password)
    mail.select("inbox")
    status, data = mail.search(None, "UNSEEN")
    if status != "OK":
        return 0
    processed = 0
    for message_id in data[0].split():
        _, raw = mail.fetch(message_id, "(RFC822)")
        message = email.message_from_bytes(raw[0][1])
        subject = _decode_value(message.get("Subject"))
        sender = _decode_value(message.get("From"))
        body = _text_body(message)
        extra_metadata = {"from": sender, "subject": subject}
        attachment_summaries: list[str] = []
        for part in message.walk():
            attachment = _attachment_bytes(part)
            if attachment is None:
                continue
            filename, payload = attachment
            attachment_path = _store_attachment(filename, payload)
            stem_slug, suffix = _normalize_attachment_name(filename)
            previous = _latest_matching_attachment(stem_slug, suffix, exclude=attachment_path)
            extra_metadata["attachment"] = attachment_path.name
            if previous and previous.exists():
                diff = generate_diff_summary(attachment_path, previous)
                attachment_summaries.append(diff["summary"])
            else:
                parsed = read_file_to_text(attachment_path)
                attachment_summaries.append(parsed.get("text", "")[:4000])
        combined_text = "\n\n".join([body, *attachment_summaries]).strip()
        ingest_text_content(
            text=combined_text,
            source="email",
            prompt_name="classify_email.txt",
            extra_metadata=extra_metadata,
        )
        mail.store(message_id, "+FLAGS", "\\Seen")
        processed += 1
    mail.logout()
    return processed


def run_forever() -> None:
    settings = get_settings()
    while True:
        try:
            count = process_unseen_messages()
            logger.info("imap_poll_processed count=%s", count)
        except Exception as exc:
            logger.warning("imap_poll_failed error=%s", exc)
        time.sleep(settings.imap_poll_interval)


if __name__ == "__main__":
    if "--once" in sys.argv:
        print(process_unseen_messages())
    else:
        run_forever()
