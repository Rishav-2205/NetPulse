"""
NetPulse Reusable Retry Mechanism.

Provides intelligent retry decorators and execution helpers with exponential backoff,
jitter, structured logging of retry attempts, and classification of transient vs deterministic failures.
"""

from functools import wraps
import random
import socket
import time
from typing import Any, Callable, Optional, Sequence, Tuple, Type, TypeVar, Union

from app.core.exceptions import (
    NetPulseError,
    TimeoutError as NetPulseTimeoutError,
    ConnectionError as NetPulseConnectionError,
    RetryExhaustedError,
    PacketValidationError,
    ConfigurationError,
)
from app.core.logging import get_logger

F = TypeVar("F", bound=Callable[..., Any])

# Default set of exception types considered transient
DEFAULT_TRANSIENT_EXCEPTIONS: Tuple[Type[BaseException], ...] = (
    socket.timeout,
    TimeoutError,
    NetPulseTimeoutError,
    NetPulseConnectionError,
    ConnectionRefusedError,
    ConnectionResetError,
    ConnectionAbortedError,
    BrokenPipeError,
    OSError,
)

# Exception types that are strictly deterministic and must NEVER be retried
DETERMINISTIC_EXCEPTIONS: Tuple[Type[BaseException], ...] = (
    PacketValidationError,
    ConfigurationError,
    ValueError,
    TypeError,
    AssertionError,
    KeyError,
    AttributeError,
)

logger = get_logger("retry")


def is_transient_network_error(exc: BaseException) -> bool:
    """
    Evaluate whether an exception is transient (retryable) or deterministic (non-retryable).
    """
    if isinstance(exc, DETERMINISTIC_EXCEPTIONS):
        return False

    # Check for requests-related network errors dynamically if imported
    exc_type_name = type(exc).__name__
    exc_module = type(exc).__module__ or ""
    if "requests.exceptions" in exc_module:
        if "Timeout" in exc_type_name or "ConnectionError" in exc_type_name:
            return True
        return False

    return isinstance(exc, DEFAULT_TRANSIENT_EXCEPTIONS)


def calculate_backoff(
    attempt: int,
    initial_delay: float,
    backoff_factor: float,
    max_delay: float = 30.0,
    jitter: bool = True
) -> float:
    """
    Calculate backoff delay in seconds with optional uniform jitter.
    """
    delay = initial_delay * (backoff_factor ** (attempt - 1))
    delay = min(delay, max_delay)
    if jitter and delay > 0:
        delay = delay * (0.5 + random.random() * 0.5)
    return delay


def retry(
    max_retries: int = 3,
    initial_delay: float = 0.1,
    backoff_factor: float = 2.0,
    max_delay: float = 10.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Union[Type[BaseException], Sequence[Type[BaseException]]]] = None,
    retry_predicate: Optional[Callable[[BaseException], bool]] = None,
    reraise_original: bool = True
) -> Callable[[F], F]:
    """
    Decorator for retrying functions on transient network failures.

    Args:
        max_retries: Maximum number of retry attempts after initial failure.
        initial_delay: Delay before the first retry attempt in seconds.
        backoff_factor: Multiplier for subsequent retry delays.
        max_delay: Maximum ceiling for delay in seconds.
        jitter: If True, adds randomness to avoid thundering herd.
        retryable_exceptions: Specific exception type(s) to retry.
        retry_predicate: Custom callable to determine if exception is retryable.
        reraise_original: If True, re-raises the original exception when retries are exhausted.
                          If False, raises RetryExhaustedError with the root cause attached.
    """
    if isinstance(retryable_exceptions, type):
        allowed_types: Tuple[Type[BaseException], ...] = (retryable_exceptions,)
    elif retryable_exceptions:
        allowed_types = tuple(retryable_exceptions)
    else:
        allowed_types = DEFAULT_TRANSIENT_EXCEPTIONS

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[BaseException] = None
            total_attempts = max_retries + 1

            for attempt in range(1, total_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except BaseException as e:
                    last_exception = e

                    # Check if error is retryable
                    is_retryable = False
                    if retry_predicate is not None:
                        is_retryable = retry_predicate(e)
                    else:
                        is_retryable = is_transient_network_error(e) and isinstance(e, allowed_types)

                    if not is_retryable or attempt >= total_attempts:
                        if not is_retryable:
                            logger.debug(
                                f"Non-retryable error in {func.__name__}: {type(e).__name__}: {e}",
                                extra={"error": str(e), "status": "FAIL"}
                            )
                        break

                    delay = calculate_backoff(attempt, initial_delay, backoff_factor, max_delay, jitter)
                    logger.warning(
                        f"Retry {attempt}/{max_retries} for {func.__name__} after {delay:.3f}s due to {type(e).__name__}: {e}",
                        extra={
                            "retry_count": attempt,
                            "error": str(e),
                            "protocol": getattr(args[0], "protocol", "UNKNOWN") if args else "UNKNOWN"
                        }
                    )
                    time.sleep(delay)

            # Exhausted retries
            if last_exception:
                logger.error(
                    f"All {max_retries} retries exhausted for {func.__name__}",
                    extra={"retry_count": max_retries, "error": str(last_exception), "status": "ERROR"}
                )
                if reraise_original:
                    raise last_exception
                raise RetryExhaustedError(
                    f"Function '{func.__name__}' failed after {max_retries} retries: {last_exception}",
                    attempts=max_retries,
                    last_exception=last_exception
                ) from last_exception

        return wrapper  # type: ignore

    return decorator


def retry_call(
    func: Callable[..., Any],
    args: Optional[Sequence[Any]] = None,
    kwargs: Optional[dict] = None,
    max_retries: int = 3,
    initial_delay: float = 0.1,
    backoff_factor: float = 2.0,
    **retry_kwargs: Any
) -> Any:
    """
    Execute a callable directly with retry logic without using a decorator.
    """
    call_args = args or ()
    call_kwargs = kwargs or {}
    decorated = retry(
        max_retries=max_retries,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor,
        **retry_kwargs
    )(func)
    return decorated(*call_args, **call_kwargs)
