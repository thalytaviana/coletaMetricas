import os
import time

import pytest

from coleta_metricas import add, classify_latency, divide, moving_average


def test_add_basic_numbers():
    assert add(2, 3) == 5


def test_divide_returns_float_result():
    assert divide(10, 4) == 2.5


def test_divide_rejects_zero_denominator():
    with pytest.raises(ValueError, match="denominator"):
        divide(10, 0)


def test_moving_average_uses_window_size():
    assert moving_average([10, 20, 30, 40], window=2) == [15, 25, 35]


def test_moving_average_returns_empty_when_window_is_too_large():
    assert moving_average([10, 20], window=3) == []


def test_moving_average_rejects_invalid_window():
    with pytest.raises(ValueError, match="window"):
        moving_average([10, 20], window=0)


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        (0.2, "fast"),
        (1.5, "regular"),
        (3.2, "slow"),
    ],
)
def test_classify_latency(duration, expected):
    assert classify_latency(duration) == expected


def test_generated_arithmetic_cases(generated_case):
    assert add(generated_case, generated_case + 1) == (generated_case * 2) + 1


@pytest.mark.slow
def test_controlled_slow_case():
    delay = float(os.getenv("SLOW_TEST_SECONDS", "0"))
    if delay > 0:
        time.sleep(delay)
    assert classify_latency(delay) in {"fast", "regular", "slow"}


def test_controlled_failure_switch():
    enabled = os.getenv("FORCE_TEST_FAILURE", "false").lower() in {"1", "true", "yes"}
    assert not enabled, "controlled failure requested by FORCE_TEST_FAILURE"
