from functools import wraps
from typing import Callable, Type, Tuple, Optional, Any
import time
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
    retry_if_exception_type,
    retry_if_result,
    RetryError
)
from utils.exceptions import ETLException, ConnectionError, EmbeddingError


def retry_on_exception(
    max_attempts: int = 3,
    wait_seconds: float = 1.0,
    exponential_backoff: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator to retry function on exceptions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        wait_seconds: Base wait time between retries (or initial wait for exponential)
        exponential_backoff: If True, wait time doubles with each retry
        exceptions: Tuple of exception types to catch and retry
    
    Example:
        @retry_on_exception(max_attempts=5, wait_seconds=2.0)
        def api_call():
            # This will retry up to 5 times with exponential backoff
            ...
    """
    def decorator(func: Callable) -> Callable:
        if exponential_backoff:
            wait_strategy = wait_exponential(multiplier=wait_seconds, min=wait_seconds, max=60)
        else:
            wait_strategy = wait_fixed(wait_seconds)
        
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_strategy,
            retry=retry_if_exception_type(exceptions),
            reraise=True
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def retry_connection(max_attempts: int = 5, wait_seconds: float = 2.0):
    """
    Decorator specifically for connection-related operations.
    Retries on ConnectionError and network-related exceptions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        wait_seconds: Base wait time between retries
    
    Example:
        @retry_connection(max_attempts=5)
        def connect_to_db():
            # Retries on connection failures
            ...
    """
    return retry_on_exception(
        max_attempts=max_attempts,
        wait_seconds=wait_seconds,
        exponential_backoff=True,
        exceptions=(ConnectionError, OSError, TimeoutError, ConnectionRefusedError)
    )


def retry_api_call(max_attempts: int = 3, wait_seconds: float = 1.0):
    """
    Decorator for API calls (OpenAI, etc.).
    Retries on EmbeddingError and rate limit errors.
    
    Args:
        max_attempts: Maximum number of retry attempts
        wait_seconds: Base wait time between retries
    
    Example:
        @retry_api_call(max_attempts=5)
        def embed_text(text):
            # Retries on API failures/rate limits
            ...
    """
    return retry_on_exception(
        max_attempts=max_attempts,
        wait_seconds=wait_seconds,
        exponential_backoff=True,
        exceptions=(
            EmbeddingError,
            ConnectionError,
            TimeoutError,
            # OpenAI rate limit errors
            Exception  # Catch all for API-specific errors
        )
    )


def retry_on_condition(
    condition: Callable[[Any], bool],
    max_attempts: int = 3,
    wait_seconds: float = 1.0
):
    """
    Retry function until condition is met (e.g., result is not None).
    
    Args:
        condition: Function that takes result and returns True to retry, False to stop
        max_attempts: Maximum number of retry attempts
        wait_seconds: Wait time between retries
    
    Example:
        @retry_on_condition(lambda x: x is None, max_attempts=5)
        def get_data():
            # Retries until result is not None
            return result
    """
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_fixed(wait_seconds),
            retry=retry_if_result(condition),
            reraise=True
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def simple_retry(
    func: Callable,
    max_attempts: int = 3,
    wait_seconds: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None
) -> Any:
    """
    Simple retry function (non-decorator version).
    Useful when you need more control over retry logic.
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        wait_seconds: Wait time between retries
        exceptions: Exceptions to catch and retry
        on_retry: Optional callback function(attempt_num, exception) called on each retry
    
    Returns:
        Function result
    
    Raises:
        Last exception if all attempts fail
    
    Example:
        result = simple_retry(
            lambda: api_call(),
            max_attempts=5,
            on_retry=lambda attempt, exc: print(f"Retry {attempt}: {exc}")
        )
    """
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts:
                if on_retry:
                    on_retry(attempt, e)
                time.sleep(wait_seconds * attempt)  # Simple exponential backoff
            else:
                break
    
    raise last_exception