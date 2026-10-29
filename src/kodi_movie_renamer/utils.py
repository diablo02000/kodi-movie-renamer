"""Utility functions for Kodi Movie Renamer."""

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing invalid characters.
    
    Args:
        filename: The filename to sanitize
    
    Returns:
        Sanitized filename
    """
    # Remove invalid characters for most filesystems
    # Windows: < > : " / \ | ? *
    # Unix: / (and null byte)
    sanitized = re.sub(r'[<>:"/\\|?*\x00]', '', filename)
    
    # Replace multiple spaces with single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    # Strip leading/trailing whitespace and dots
    sanitized = sanitized.strip().strip('.')
    
    return sanitized


def extract_year_from_string(text: str) -> int | None:
    """Extract a 4-digit year from a string.
    
    Args:
        text: String to extract year from
    
    Returns:
        Extracted year or None
    """
    # Look for 4-digit number that might be a year
    # Common patterns: (1999), [2000], 2001, 1999.
    year_match = re.search(r'(?:[(\[{])?(\d{4})[)}\]{])|\b(\d{4})\b', text)
    
    if year_match:
        # Get first group that matched
        for group in year_match.groups():
            if group:
                try:
                    year = int(group)
                    # Basic validation: year should be reasonable
                    if 1900 <= year <= 2100:
                        return year
                except ValueError:
                    pass
    
    return None


def parse_filename_to_parts(filename: str) -> dict[str, str | int | None]:
    """Parse a filename into its components.
    
    Args:
        filename: The filename to parse
    
    Returns:
        Dictionary with parsed components
    """
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    
    # Extract year
    year = extract_year_from_string(stem)
    
    # Remove year from stem
    if year:
        stem = re.sub(r'[(\[{])?\d{4}[)}\]{}]', '', stem)
    
    # Clean up the stem
    stem = re.sub(r'[._-]+', ' ', stem).strip()
    
    return {
        "original": filename,
        "stem": stem,
        "suffix": suffix,
        "year": year,
    }


def get_video_extensions() -> set[str]:
    """Get a set of common video file extensions.
    
    Returns:
        Set of video file extensions (lowercase, with dot)
    """
    return {
        '.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.m4v',
        '.mpg', '.mpeg', '.3gp', '.3g2', '.m2ts', '.ts', '.webm',
        '.ogv', '.m2v', '.vob', '.divx', '.f4v'
    }


def is_video_file(path: Path | str) -> bool:
    """Check if a path is a video file.
    
    Args:
        path: Path to check
    
    Returns:
        True if the path is a video file
    """
    path = Path(path)
    video_extensions = get_video_extensions()
    return path.is_file() and path.suffix.lower() in video_extensions


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Human-readable size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"
