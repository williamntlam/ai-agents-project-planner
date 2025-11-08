"""Retry decorators for LLM API calls."""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from openai import RateLimitError, APIError


def retry_llm_call(max_attempts: int = 3):
    """
    Decorator for retrying LLM API calls.
    
    Args:
        max_attempts: Maximum number of retry attempts
        
    Returns:
        Decorator function
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, APIError)),
        reraise=True
    )

