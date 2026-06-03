"""Funcoes simples para exercitar lint, testes e variacoes do pipeline."""

from collections.abc import Sequence


def add(left: float, right: float) -> float:
    return left + right


def divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        msg = "denominator must not be zero"
        raise ValueError(msg)
    return numerator / denominator


def moving_average(values: Sequence[float], window: int) -> list[float]:
    if window <= 0:
        msg = "window must be positive"
        raise ValueError(msg)
    if window > len(values):
        return []

    averages: list[float] = []
    for index in range(len(values) - window + 1):
        chunk = values[index : index + window]
        averages.append(sum(chunk) / window)
    return averages


def classify_latency(duration_seconds: float) -> str:
    if duration_seconds < 0:
        msg = "duration must not be negative"
        raise ValueError(msg)
    if duration_seconds < 1:
        return "fast"
    if duration_seconds < 3:
        return "regular"
    return "slow"
