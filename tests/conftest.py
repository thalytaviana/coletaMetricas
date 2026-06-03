"""Configuracao de testes para variar o volume de casos pelo ambiente."""

import os


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value)
    except ValueError:
        return default


def pytest_generate_tests(metafunc):
    if "generated_case" in metafunc.fixturenames:
        case_count = max(1, _int_env("EXTRA_TEST_CASES", 8))
        metafunc.parametrize("generated_case", range(case_count))
