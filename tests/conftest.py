"""Mock heavy optional dependencies so unit tests run without installing ML packages."""
import sys
from unittest.mock import MagicMock

_HEAVY = [
    "chromadb",
    "chromadb.config",
    "chromadb.api",
    "chromadb.api.models",
    "sentence_transformers",
    "faster_whisper",
    "openpyxl",
    "docx",
    "pdfplumber",
    "PIL",
    "PIL.Image",
    "pytesseract",
    "schedule",
    "flask",
    "fastmcp",
    "fastmcp.server",
    "fastmcp.server.auth",
    "fastmcp.server.auth.auth",
    "git",
]

for _mod in _HEAVY:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
