"""
Utility helpers for working with clip and segment file paths.

These helpers keep path normalization consistent between backend services,
scripts, and tests. The goal is to preserve intentional "../" sequences while
still allowing us to store paths in a relative `./uploads/...` format that is
portable across machines.
"""

from __future__ import annotations

import os


def strip_leading_dot_slash(path: str) -> str:
    """
    Remove a single leading "./" prefix while preserving "../" sequences.

    Args:
        path: File path that may start with "./".

    Returns:
        Path without the first "./" prefix. If no such prefix exists, the
        original string is returned untouched.
    """
    if path.startswith("./"):
        return path[2:]
    return path


def to_relative_upload_path(path: str, upload_root: str) -> str:
    """
    Convert an absolute clip path into a portable ./uploads/... path.

    Args:
        path: Absolute path to the clip on disk.
        upload_root: Base uploads directory from settings.upload_dir.

    Returns:
        A normalized string starting with "./uploads/..." when the file lives
        under the configured uploads directory. If the file is outside that
        root, the original absolute path is returned unchanged.
    """
    absolute_path = os.path.abspath(path)
    uploads_root_abs = os.path.abspath(upload_root)

    try:
        common_root = os.path.commonpath([absolute_path, uploads_root_abs])
    except ValueError:
        # os.path.commonpath raises when drives differ (e.g., Windows). Fall
        # back to returning the absolute path unchanged in that scenario.
        return absolute_path

    if common_root != uploads_root_abs:
        return absolute_path

    relative_path = os.path.relpath(absolute_path, uploads_root_abs)
    normalized = os.path.join("uploads", relative_path).replace("\\", "/")

    if not normalized.startswith("./"):
        normalized = "./" + normalized
    return normalized

