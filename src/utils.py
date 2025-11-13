"""
Utility functions for the baby monitoring application.
Provides helpers for file handling, JSON parsing, and async operations.
"""
import json
import re
import asyncio
from pathlib import Path
from typing import Any, Dict, Callable, TypeVar, Optional
from datetime import datetime
from functools import wraps
import uuid


T = TypeVar('T')


def save_bytes_to_temp(image_bytes: bytes, suffix: str = ".jpg") -> str:
    """
    Save bytes to a temporary file in the temp/ directory (synchronous).
    
    Args:
        image_bytes: Raw bytes to save
        suffix: File extension (default: ".jpg")
    
    Returns:
        str: Path to the saved file
    
    Raises:
        IOError: If unable to write file
    """
    from src.config import ensure_directories
    
    # Ensure temp directory exists
    ensure_directories()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    temp_dir = project_root / "temp"
    
    # Generate unique filename with timestamp and UUID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    
    # Ensure suffix starts with a dot
    if not suffix.startswith('.'):
        suffix = f".{suffix}"
    
    filename = f"frame_{timestamp}_{unique_id}{suffix}"
    filepath = temp_dir / filename
    
    # Write bytes to file
    try:
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        return str(filepath)
    except Exception as e:
        raise IOError(f"Failed to save bytes to {filepath}: {str(e)}")


async def save_bytes_to_temp_async(image_bytes: bytes, suffix: str = ".jpg") -> str:
    """
    Save bytes to a temporary file in the temp/ directory (asynchronous with aiofiles).
    
    Args:
        image_bytes: Raw bytes to save
        suffix: File extension (default: ".jpg")
    
    Returns:
        str: Path to the saved file
    
    Raises:
        IOError: If unable to write file
    """
    import aiofiles
    from src.config import ensure_directories
    
    # Ensure temp directory exists
    ensure_directories()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    temp_dir = project_root / "temp"
    
    # Generate unique filename with timestamp and UUID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    
    # Ensure suffix starts with a dot
    if not suffix.startswith('.'):
        suffix = f".{suffix}"
    
    filename = f"frame_{timestamp}_{unique_id}{suffix}"
    filepath = temp_dir / filename
    
    # Write bytes to file asynchronously
    try:
        async with aiofiles.open(filepath, 'wb') as f:
            await f.write(image_bytes)
        return str(filepath)
    except Exception as e:
        raise IOError(f"Failed to save bytes to {filepath}: {str(e)}")


def load_json_safe(text: str) -> Dict[str, Any]:
    """
    Safely parse JSON text with automatic code fence stripping.
    Returns raw text in a dict if parsing fails.
    
    Args:
        text: String containing JSON (possibly with markdown code fences)
    
    Returns:
        Dict: Parsed JSON object, or {"_raw": text, "_error": error_msg} on failure
    """
    if not text:
        return {"_raw": "", "_error": "Empty input"}
    
    try:
        # Strip whitespace
        cleaned = text.strip()
        
        # Remove markdown code fences
        # Patterns: ```json\n...\n``` or ```\n...\n```
        cleaned = re.sub(r'^```(?:json|python|javascript|yaml)?\s*\n', '', cleaned)
        cleaned = re.sub(r'\n```\s*$', '', cleaned)
        cleaned = cleaned.strip()
        
        # Try to parse JSON
        parsed = json.loads(cleaned)
        return parsed
    
    except json.JSONDecodeError as e:
        return {
            "_raw": text,
            "_error": f"JSON parse error: {str(e)}"
        }
    
    except Exception as e:
        return {
            "_raw": text,
            "_error": f"Unexpected error: {str(e)}"
        }


async def run_blocking(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run a blocking/synchronous function in a thread pool executor.
    Useful for calling sync functions from async code without blocking the event loop.
    
    Args:
        func: Synchronous function to run
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func
    
    Returns:
        The result of func(*args, **kwargs)
    
    Example:
        result = await run_blocking(some_sync_function, arg1, arg2)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


def make_async(func: Callable[..., T]) -> Callable[..., asyncio.Future[T]]:
    """
    Decorator to convert a synchronous function to async using thread pool.
    
    Args:
        func: Synchronous function to convert
    
    Returns:
        Async function that runs the original in a thread pool
    
    Example:
        @make_async
        def blocking_operation(x):
            time.sleep(1)
            return x * 2
        
        result = await blocking_operation(5)
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> T:
        return await run_blocking(func, *args, **kwargs)
    
    return async_wrapper


def cleanup_temp_files(older_than_hours: int = 24) -> int:
    """
    Clean up old files from the temp/ directory.
    
    Args:
        older_than_hours: Delete files older than this many hours (default: 24)
    
    Returns:
        int: Number of files deleted
    """
    from src.config import ensure_directories
    from datetime import timedelta
    
    ensure_directories()
    
    project_root = Path(__file__).parent.parent
    temp_dir = project_root / "temp"
    
    cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
    deleted_count = 0
    
    try:
        for file_path in temp_dir.glob("*"):
            # Skip directories and .gitkeep
            if file_path.is_dir() or file_path.name == ".gitkeep":
                continue
            
            # Check file modification time
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            if file_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️  Failed to delete {file_path}: {e}")
    
    except Exception as e:
        print(f"⚠️  Error during cleanup: {e}")
    
    return deleted_count


def get_temp_file_count() -> int:
    """
    Get the number of files in the temp/ directory.
    
    Returns:
        int: Number of files (excluding directories and .gitkeep)
    """
    project_root = Path(__file__).parent.parent
    temp_dir = project_root / "temp"
    
    if not temp_dir.exists():
        return 0
    
    return sum(1 for f in temp_dir.glob("*") if f.is_file() and f.name != ".gitkeep")


def format_timestamp(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a datetime object as a string.
    
    Args:
        dt: Datetime object (default: now)
        format_str: Format string (default: "%Y-%m-%d %H:%M:%S")
    
    Returns:
        str: Formatted timestamp
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(format_str)


def extract_base64_from_data_url(data_url: str) -> Optional[bytes]:
    """
    Extract base64 bytes from a data URL.
    
    Args:
        data_url: Data URL string (e.g., "data:image/jpeg;base64,...")
    
    Returns:
        bytes: Decoded bytes, or None if invalid
    """
    import base64
    
    try:
        # Split on comma to get base64 part
        if ',' not in data_url:
            return None
        
        base64_str = data_url.split(',', 1)[1]
        return base64.b64decode(base64_str)
    
    except Exception as e:
        print(f"⚠️  Failed to decode data URL: {e}")
        return None


def validate_image_bytes(image_bytes: bytes, max_size_mb: int = 10) -> tuple[bool, Optional[str]]:
    """
    Validate image bytes for size and basic format.
    
    Args:
        image_bytes: Raw image bytes
        max_size_mb: Maximum allowed size in MB (default: 10)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check size
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"Image too large: {size_mb:.2f}MB (max: {max_size_mb}MB)"
    
    # Check if empty
    if len(image_bytes) == 0:
        return False, "Image is empty"
    
    # Check for common image format headers
    # JPEG: FF D8 FF
    # PNG: 89 50 4E 47
    # GIF: 47 49 46 38
    valid_formats = {
        b'\xff\xd8\xff': 'JPEG',
        b'\x89PNG': 'PNG',
        b'GIF8': 'GIF'
    }
    
    is_valid_format = any(image_bytes.startswith(sig) for sig in valid_formats.keys())
    
    if not is_valid_format:
        return False, "Invalid image format (expected JPEG, PNG, or GIF)"
    
    return True, None


def dict_safe_get(data: dict, *keys, default=None) -> Any:
    """
    Safely get nested dictionary values.
    
    Args:
        data: Dictionary to search
        *keys: Sequence of keys to traverse
        default: Default value if key path doesn't exist
    
    Returns:
        Value at the key path, or default if not found
    
    Example:
        value = dict_safe_get(data, "user", "profile", "name", default="Unknown")
    """
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


if __name__ == "__main__":
    # Test utilities
    print("=" * 60)
    print("UTILITY FUNCTIONS TEST")
    print("=" * 60)
    
    # Test 1: save_bytes_to_temp
    print("\n[Test 1] save_bytes_to_temp:")
    test_bytes = b"Hello, this is a test image"
    filepath = save_bytes_to_temp(test_bytes, suffix=".jpg")
    print(f"  ✅ Saved to: {filepath}")
    print(f"  📁 Temp files count: {get_temp_file_count()}")
    
    # Test 2: load_json_safe with valid JSON
    print("\n[Test 2] load_json_safe with valid JSON:")
    json_text = '{"name": "test", "value": 123}'
    result = load_json_safe(json_text)
    print(f"  ✅ Parsed: {result}")
    
    # Test 3: load_json_safe with code fences
    print("\n[Test 3] load_json_safe with code fences:")
    json_with_fences = '```json\n{"name": "test", "value": 456}\n```'
    result = load_json_safe(json_with_fences)
    print(f"  ✅ Parsed: {result}")
    
    # Test 4: load_json_safe with invalid JSON
    print("\n[Test 4] load_json_safe with invalid JSON:")
    invalid_json = "not valid json at all"
    result = load_json_safe(invalid_json)
    print(f"  ⚠️  Error handled: {result.get('_error')}")
    
    # Test 5: validate_image_bytes
    print("\n[Test 5] validate_image_bytes:")
    jpeg_header = b'\xff\xd8\xff' + b'fake jpeg data'
    is_valid, error = validate_image_bytes(jpeg_header)
    print(f"  ✅ Valid JPEG: {is_valid}, Error: {error}")
    
    # Test 6: dict_safe_get
    print("\n[Test 6] dict_safe_get:")
    test_dict = {"user": {"profile": {"name": "Alice"}}}
    name = dict_safe_get(test_dict, "user", "profile", "name", default="Unknown")
    missing = dict_safe_get(test_dict, "user", "settings", "theme", default="default")
    print(f"  ✅ Found name: {name}")
    print(f"  ✅ Default for missing: {missing}")
    
    # Test 7: format_timestamp
    print("\n[Test 7] format_timestamp:")
    timestamp = format_timestamp()
    print(f"  ✅ Current time: {timestamp}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
