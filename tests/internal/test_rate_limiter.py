import mock
import time

import pytest

from ddtrace.internal.rate_limiter import RateLimiter


def test_rate_limiter_init():
    limiter = RateLimiter(rate_limit=100)
    assert limiter.rate_limit == 100
    assert limiter.tokens == 100
    assert limiter.max_tokens == 100
    assert limiter.last_update <= time.time()


def test_rate_limiter_rate_limit_0():
    limiter = RateLimiter(rate_limit=0)
    assert limiter.rate_limit == 0
    assert limiter.tokens == 0
    assert limiter.max_tokens == 0

    now = time.time()
    with mock.patch('time.time') as mock_time:
        for i in range(10000):
            # Make sure the time is different for every check
            mock_time.return_value = now + i
            assert limiter.is_allowed() is False


def test_rate_limiter_rate_limit_negative():
    limiter = RateLimiter(rate_limit=-1)
    assert limiter.rate_limit == -1
    assert limiter.tokens == -1
    assert limiter.max_tokens == -1

    now = time.time()
    with mock.patch('time.time') as mock_time:
        for i in range(10000):
            # Make sure the time is different for every check
            mock_time.return_value = now + i
            assert limiter.is_allowed() is True


@pytest.mark.parametrize('rate_limit', [1, 10, 50, 100, 500, 1000])
def test_rate_limiter_is_allowed(rate_limit):
    limiter = RateLimiter(rate_limit=rate_limit)

    def check_limit():
        # Up to the allowed limit is allowed
        for _ in range(rate_limit):
            assert limiter.is_allowed()

        # Any over the limit is disallowed
        for _ in range(1000):
            assert limiter.is_allowed() is False

    # Start time
    now = time.time()

    # Check the limit for 5 time frames
    for i in range(5):
        with mock.patch('time.time') as mock_time:
            # Keep the same timeframe
            mock_time.return_value = now + i

            check_limit()


def test_rate_limiter_is_allowed_large_gap():
    limiter = RateLimiter(rate_limit=100)

    # Start time
    now = time.time()
    with mock.patch('time.time') as mock_time:
        # Keep the same timeframe
        mock_time.return_value = now

        for _ in range(100):
            assert limiter.is_allowed()

    # Large gap before next call to `is_allowed()`
    with mock.patch('time.time') as mock_time:
        mock_time.return_value = now + 100

        for _ in range(100):
            assert limiter.is_allowed()


def test_rate_limiter_is_allowed_small_gaps():
    limiter = RateLimiter(rate_limit=100)

    # Start time
    now = time.time()
    gap = 1 / 100
    # Keep incrementing by a gap to keep us at our rate limit
    with mock.patch('time.time') as mock_time:
        for i in range(10000):
            # Keep the same timeframe
            mock_time.return_value = now + (gap * i)

            assert limiter.is_allowed()
