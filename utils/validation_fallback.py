#!/usr/bin/env python3
"""
Validation Fallback Wrapper

Provides graceful degradation for AI-powered validators when API calls fail.

Features:
1. Decorator pattern for wrapping AI validation functions
2. Automatic fallback to heuristic-only validation on API errors
3. Clear reporting of AI failures vs validation failures
4. Retry logic with exponential backoff
5. Result caching to avoid repeated API calls

Addresses Priority 4: Graceful API Failure Handling
"""

import logging
import time
import functools
from typing import Callable, Any, Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ValidationMode(Enum):
    """Validation mode"""
    AI_POWERED = "ai_powered"  # Use AI for validation
    HEURISTIC_ONLY = "heuristic_only"  # Use only rule-based heuristics
    HYBRID = "hybrid"  # Try AI, fall back to heuristics


@dataclass
class ValidationResult:
    """Wrapper for validation results with metadata"""
    success: bool
    result: Any  # Actual validation result
    mode_used: ValidationMode
    ai_failed: bool = False
    ai_error: Optional[str] = None
    fallback_used: bool = False
    retry_count: int = 0
    duration_ms: float = 0.0


class ValidationFallbackWrapper:
    """
    Wrapper that provides graceful degradation for AI validators.

    Usage:
        wrapper = ValidationFallbackWrapper(
            max_retries=3,
            retry_delay=2.0,
            enable_cache=True
        )

        @wrapper.with_fallback(heuristic_func=basic_validation)
        def ai_validation(data):
            # AI validation that might fail
            return call_openai(data)
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        exponential_backoff: bool = True,
        enable_cache: bool = False
    ):
        """
        Initialize wrapper.

        Args:
            max_retries: Maximum number of retries for API calls
            retry_delay: Base delay between retries (seconds)
            exponential_backoff: If True, delay doubles after each retry
            enable_cache: If True, cache results to avoid repeated API calls
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
        self.enable_cache = enable_cache
        self.cache: Dict[str, Any] = {}

    def with_fallback(
        self,
        heuristic_func: Optional[Callable] = None,
        mode: ValidationMode = ValidationMode.HYBRID,
        cache_key_func: Optional[Callable] = None
    ):
        """
        Decorator that adds fallback behavior to a validation function.

        Args:
            heuristic_func: Fallback function to use if AI fails
            mode: Validation mode (AI_POWERED, HEURISTIC_ONLY, or HYBRID)
            cache_key_func: Function to generate cache key from args

        Returns:
            Decorated function with fallback behavior
        """
        def decorator(ai_func: Callable) -> Callable:
            @functools.wraps(ai_func)
            def wrapper(*args, **kwargs) -> ValidationResult:
                start_time = time.time()

                # Check cache if enabled
                cache_key = None
                if self.enable_cache and cache_key_func:
                    try:
                        cache_key = cache_key_func(*args, **kwargs)
                        if cache_key in self.cache:
                            cached_result = self.cache[cache_key]
                            logger.info(f"✓ Using cached validation result for {cache_key}")
                            return cached_result
                    except Exception as e:
                        logger.warning(f"Cache key generation failed: {e}")

                # HEURISTIC_ONLY mode - skip AI entirely
                if mode == ValidationMode.HEURISTIC_ONLY:
                    if heuristic_func:
                        logger.info("Using heuristic-only validation (AI disabled)")
                        result = heuristic_func(*args, **kwargs)
                        duration_ms = (time.time() - start_time) * 1000

                        validation_result = ValidationResult(
                            success=True,
                            result=result,
                            mode_used=ValidationMode.HEURISTIC_ONLY,
                            duration_ms=duration_ms
                        )

                        if self.enable_cache and cache_key:
                            self.cache[cache_key] = validation_result

                        return validation_result
                    else:
                        logger.error("HEURISTIC_ONLY mode but no heuristic function provided")
                        return ValidationResult(
                            success=False,
                            result=None,
                            mode_used=ValidationMode.HEURISTIC_ONLY,
                            ai_failed=True,
                            ai_error="No heuristic function provided"
                        )

                # AI_POWERED or HYBRID mode - try AI with retries
                last_error = None
                retry_count = 0

                for attempt in range(self.max_retries + 1):
                    try:
                        logger.debug(f"AI validation attempt {attempt + 1}/{self.max_retries + 1}")

                        result = ai_func(*args, **kwargs)
                        duration_ms = (time.time() - start_time) * 1000

                        logger.info(f"✓ AI validation succeeded (attempt {attempt + 1}, {duration_ms:.0f}ms)")

                        validation_result = ValidationResult(
                            success=True,
                            result=result,
                            mode_used=ValidationMode.AI_POWERED,
                            retry_count=attempt,
                            duration_ms=duration_ms
                        )

                        if self.enable_cache and cache_key:
                            self.cache[cache_key] = validation_result

                        return validation_result

                    except Exception as e:
                        last_error = str(e)
                        retry_count = attempt + 1

                        # Check if it's a retryable error
                        if self._is_retryable_error(e):
                            if attempt < self.max_retries:
                                delay = self._calculate_delay(attempt)
                                logger.warning(
                                    f"AI validation failed (attempt {attempt + 1}): {e}. "
                                    f"Retrying in {delay}s..."
                                )
                                time.sleep(delay)
                                continue
                            else:
                                logger.error(
                                    f"AI validation failed after {self.max_retries + 1} attempts: {e}"
                                )
                        else:
                            logger.error(f"AI validation failed with non-retryable error: {e}")
                            break

                # AI failed - use fallback if HYBRID mode
                duration_ms = (time.time() - start_time) * 1000

                if mode == ValidationMode.HYBRID and heuristic_func:
                    logger.warning("AI validation failed - falling back to heuristic validation")

                    try:
                        result = heuristic_func(*args, **kwargs)

                        validation_result = ValidationResult(
                            success=True,
                            result=result,
                            mode_used=ValidationMode.HEURISTIC_ONLY,
                            ai_failed=True,
                            ai_error=last_error,
                            fallback_used=True,
                            retry_count=retry_count,
                            duration_ms=duration_ms
                        )

                        if self.enable_cache and cache_key:
                            self.cache[cache_key] = validation_result

                        return validation_result

                    except Exception as fallback_error:
                        logger.error(f"Fallback validation also failed: {fallback_error}")
                        return ValidationResult(
                            success=False,
                            result=None,
                            mode_used=ValidationMode.HEURISTIC_ONLY,
                            ai_failed=True,
                            ai_error=last_error,
                            fallback_used=True,
                            retry_count=retry_count,
                            duration_ms=duration_ms
                        )
                else:
                    # No fallback available
                    logger.error("AI validation failed and no fallback available")
                    return ValidationResult(
                        success=False,
                        result=None,
                        mode_used=ValidationMode.AI_POWERED,
                        ai_failed=True,
                        ai_error=last_error,
                        retry_count=retry_count,
                        duration_ms=duration_ms
                    )

            return wrapper
        return decorator

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retryable.

        Args:
            error: Exception that occurred

        Returns:
            True if error is retryable (network, rate limit, timeout)
        """
        error_str = str(error).lower()

        # Retryable error patterns
        retryable_patterns = [
            'rate limit',
            'timeout',
            'connection',
            'network',
            '429',  # Too many requests
            '500',  # Internal server error
            '502',  # Bad gateway
            '503',  # Service unavailable
            '504',  # Gateway timeout
        ]

        # Non-retryable error patterns
        non_retryable_patterns = [
            '401',  # Unauthorized (API key issue)
            '403',  # Forbidden
            '404',  # Not found
            'invalid api key',
            'authentication',
        ]

        # Check non-retryable first
        for pattern in non_retryable_patterns:
            if pattern in error_str:
                return False

        # Check retryable
        for pattern in retryable_patterns:
            if pattern in error_str:
                return True

        # Default: don't retry unknown errors
        return False

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        if self.exponential_backoff:
            return self.retry_delay * (2 ** attempt)
        else:
            return self.retry_delay


# Global wrapper instance
default_wrapper = ValidationFallbackWrapper(
    max_retries=3,
    retry_delay=2.0,
    exponential_backoff=True,
    enable_cache=False
)


def with_fallback(heuristic_func: Optional[Callable] = None, mode: ValidationMode = ValidationMode.HYBRID):
    """
    Convenience decorator using default wrapper.

    Usage:
        @with_fallback(heuristic_func=basic_validation)
        def ai_validation(data):
            return call_openai(data)
    """
    return default_wrapper.with_fallback(heuristic_func=heuristic_func, mode=mode)


def main():
    """Test the fallback wrapper"""
    print("\n" + "="*80)
    print("VALIDATION FALLBACK WRAPPER TEST")
    print("="*80 + "\n")

    wrapper = ValidationFallbackWrapper(max_retries=2, retry_delay=0.5)

    # Mock functions
    def ai_validator(data):
        """Simulated AI validator that fails"""
        raise Exception("OpenAI API rate limit exceeded (429)")

    def heuristic_validator(data):
        """Simulated heuristic validator that always works"""
        return {"valid": True, "method": "heuristic"}

    # Apply wrapper
    @wrapper.with_fallback(heuristic_func=heuristic_validator, mode=ValidationMode.HYBRID)
    def validate_data(data):
        return ai_validator(data)

    # Test
    result = validate_data({"test": "data"})

    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Mode Used: {result.mode_used.value}")
    print(f"  AI Failed: {result.ai_failed}")
    print(f"  Fallback Used: {result.fallback_used}")
    print(f"  Retry Count: {result.retry_count}")
    print(f"  Duration: {result.duration_ms:.0f}ms")

    if result.result:
        print(f"  Result: {result.result}")

    print("\n" + "="*80)
    print("✓ TEST COMPLETE")
    print("="*80 + "\n")

    return 0


if __name__ == "__main__":
    exit(main())
