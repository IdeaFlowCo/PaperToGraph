"""
Utilities for converting various document formats to text.
"""

from markitdown import MarkItDown
from utils import log_msg

_md_converter = None


def init_converter():
    """Initialize the MarkItDown converter."""
    global _md_converter
    if _md_converter is None:
        _md_converter = MarkItDown()


def convert_to_text(file_path: str) -> str:
    """
    Convert a document to plain text using MarkItDown.
    Currently supports: PDF, Word, Excel, PowerPoint, Images, HTML, and text-based formats.
    """
    init_converter()
    try:
        result = _md_converter.convert(file_path)
        return result.text_content
    except Exception as e:
        log_msg(f"Error converting file {file_path}: {e}")
        raise
