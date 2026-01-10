"""
File storage utilities for handling uploads
"""
import os
import re
import shutil
import aiofiles
from pathlib import Path
from typing import Optional
from fastapi import UploadFile


# Base storage directory
STORAGE_BASE = Path(__file__).parent.parent.parent / "storage"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by replacing problematic characters with safe alternatives

    - Spaces -> underscores
    - Parentheses -> underscores
    - Other special chars -> underscores (except letters, digits, dot, hyphen, underscore)
    """
    if not filename:
        return "unnamed_file"

    # Get name and extension
    name, ext = os.path.splitext(filename)

    # Replace problematic characters with underscores
    # Keep only: letters, digits, dot, hyphen, underscore
    safe_name = re.sub(r'[^\w\-.]', '_', name, flags=re.ASCII)

    # Remove multiple consecutive underscores
    safe_name = re.sub(r'_+', '_', safe_name).strip('_')

    # If empty after sanitization, use default
    if not safe_name:
        safe_name = "unnamed_file"

    return safe_name + ext


async def save_upload_file(
    upload_file: UploadFile,
    subdirectory: str = "uploads/"
) -> str:
    """
    Save uploaded file to storage directory

    Args:
        upload_file: FastAPI UploadFile object
        subdirectory: Subdirectory within storage (e.g., "uploads/", "uploads/channels/")

    Returns:
        Full path to saved file
    """
    # Create directory if it doesn't exist
    target_dir = STORAGE_BASE / subdirectory.lstrip("/")
    target_dir.mkdir(parents=True, exist_ok=True)

    # Generate safe filename using the new sanitization function
    filename = sanitize_filename(upload_file.filename or "uploaded_file")

    file_path = target_dir / filename

    # Handle duplicate filenames
    counter = 1
    while file_path.exists():
        name, ext = os.path.splitext(filename)
        file_path = target_dir / f"{name}_{counter}{ext}"
        counter += 1

    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        content = await upload_file.read()
        await f.write(content)

    return str(file_path)


def save_upload_file_sync(
    file_path: str,
    subdirectory: str = "uploads/"
) -> str:
    """
    Save a file from path to storage directory (synchronous)

    Args:
        file_path: Source file path
        subdirectory: Subdirectory within storage

    Returns:
        Full path to saved file
    """
    # Create directory if it doesn't exist
    target_dir = STORAGE_BASE / subdirectory.lstrip("/")
    target_dir.mkdir(parents=True, exist_ok=True)

    # Get filename
    filename = Path(file_path).name
    target_path = target_dir / filename

    # Copy file
    shutil.copy(file_path, target_path)

    return str(target_path)


def cleanup_file(file_path: str) -> bool:
    """
    Delete a file from storage

    Args:
        file_path: Path to file to delete

    Returns:
        True if deleted successfully
    """
    try:
        Path(file_path).unlink()
        return True
    except Exception:
        return False


def cleanup_directory(subdirectory: str = "uploads/") -> int:
    """
    Clean up all files in a directory

    Args:
        subdirectory: Subdirectory within storage

    Returns:
        Number of files deleted
    """
    target_dir = STORAGE_BASE / subdirectory.lstrip("/")
    if not target_dir.exists():
        return 0

    count = 0
    for file_path in target_dir.glob("*"):
        if file_path.is_file():
            file_path.unlink()
            count += 1

    return count


def get_storage_path(subdirectory: str = "") -> Path:
    """Get full path to a storage subdirectory"""
    if subdirectory:
        return STORAGE_BASE / subdirectory.lstrip("/")
    return STORAGE_BASE


def ensure_storage_dirs():
    """Ensure all storage directories exist"""
    dirs = [
        "uploads",
        "uploads/channels",
        "outputs"
    ]
    for d in dirs:
        (STORAGE_BASE / d).mkdir(parents=True, exist_ok=True)


# Initialize storage directories on import
ensure_storage_dirs()
