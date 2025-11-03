import hashlib
from typing import Union


def generate_hash(content: str, algorithm: str = "sha256") -> str:
    """
    Generate hash of content for deduplication.
    
    Args:
        content: Content string to hash
        algorithm: Hash algorithm ('md5', 'sha256', 'sha1', etc.)
    
    Returns:
        Hexadecimal hash string
    
    Example:
        >>> generate_hash("Hello world")
        '64ec88ca00b268e5ba1a35678a1b5316d212f4f366b2477232534a8aeca37f3c'
    """
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(content.encode('utf-8'))
    return hash_obj.hexdigest()


def secure_hash(content: str) -> str:
    """
    Generate secure hash using SHA256.
    Use this if you need cryptographically secure hashing.
    
    Args:
        content: Content string to hash
    
    Returns:
        SHA256 hexadecimal hash string
    """
    return generate_hash(content, algorithm="sha256")


def hash_file(file_path: Union[str, bytes], chunk_size: int = 8192) -> str:
    """
    Generate hash of a file without loading entire file into memory.
    
    Args:
        file_path: Path to file
        chunk_size: Size of chunks to read (default 8KB)
    
    Returns:
        SHA256 hexadecimal hash string
    """
    hash_obj = hashlib.sha256()
    
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def normalize_content_for_hashing(content: str) -> str:
    """
    Normalize content before hashing to catch near-duplicates.
    
    Args:
        content: Content to normalize
    
    Returns:
        Normalized content (lowercase, whitespace normalized)
    
    Example:
        "Hello   World" -> "hello world"
        "Hello\nWorld" -> "hello world"
    """
    # Lowercase, strip whitespace, normalize spaces
    normalized = content.lower().strip()
    # Replace multiple whitespace with single space
    import re
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def generate_hash_for_normalized_content(content: str) -> str:
    """
    Generate hash of normalized content (catches near-duplicates).
    
    Args:
        content: Content string to hash
    
    Returns:
        Hexadecimal hash string
    
    Use this if you want to catch duplicates even with slight formatting differences.
    """
    normalized = normalize_content_for_hashing(content)
    return generate_hash(normalized)