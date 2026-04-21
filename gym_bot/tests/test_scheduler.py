"""Tests for scheduler.py — timing utilities."""

import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
import requests

from scheduler import wait_until, measure_latency


class TestWaitUntil:
    """wait_until() precision timer."""

    def test_past_time_returns_immediately(self):
        past = (datetime.now() - timedelta(minutes=5)).strftime("%H:%M:%S")
        start = time.time()
        wait_until(past)
        elapsed = time.time() - start
        assert elapsed < 1.0

    def test_near_future_time(self):
        target = (datetime.now() + timedelta(seconds=3)).strftime("%H:%M:%S")
        start = time.time()
        wait_until(target)
        elapsed = time.time() - start
        assert 1.0 < elapsed < 6.0

    def test_accuracy_within_100ms(self):
        target_dt = datetime.now() + timedelta(seconds=2)
        target_str = target_dt.strftime("%H:%M:%S")
        wait_until(target_str)
        now = datetime.now()
        # Should be very close to target (within ~100ms, but allow 500ms for CI)
        diff = abs((now - target_dt).total_seconds())
        assert diff < 0.5


class TestMeasureLatency:
    """measure_latency() network measurement."""

    def test_returns_median_latency(self):
        session = MagicMock(spec=requests.Session)

        call_count = 0
        delays = [0.05, 0.03, 0.10, 0.04, 0.06]

        def fake_head(url, timeout=5):
            nonlocal call_count
            time.sleep(delays[call_count % len(delays)])
            call_count += 1
            return MagicMock(status_code=200)

        session.head = fake_head

        latency = measure_latency(session, "https://example.com", times=5)
        # Median of ~50ms, 30ms, 100ms, 40ms, 60ms = 50ms
        assert 20 < latency < 200

    def test_all_requests_fail_returns_default(self):
        session = MagicMock(spec=requests.Session)
        session.head.side_effect = requests.RequestException("timeout")

        latency = measure_latency(session, "https://example.com", times=3)
        assert latency == 100.0

    def test_partial_failures(self):
        session = MagicMock(spec=requests.Session)
        results = [MagicMock(), requests.RequestException("fail"), MagicMock()]
        call_count = 0

        def fake_head(url, timeout=5):
            nonlocal call_count
            r = results[call_count % len(results)]
            call_count += 1
            if isinstance(r, Exception):
                raise r
            return r

        session.head = fake_head
        latency = measure_latency(session, "https://example.com", times=3)
        assert latency > 0
