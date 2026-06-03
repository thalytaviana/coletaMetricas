from __future__ import annotations

import argparse
import json
import os
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _int_attr(element: ET.Element, name: str) -> int:
    value = element.attrib.get(name, "0")
    try:
        return int(value)
    except ValueError:
        return int(float(value))


def _float_attr(element: ET.Element, name: str) -> float:
    value = element.attrib.get(name, "0")
    try:
        return float(value)
    except ValueError:
        return 0.0


def summarize(junit_xml: Path) -> dict[str, object]:
    tree = ET.parse(junit_xml)
    root = tree.getroot()

    suites = [item for item in root.iter() if _local_name(item.tag) == "testsuite"]
    test_cases = [item for item in root.iter() if _local_name(item.tag) == "testcase"]

    if root.attrib.get("tests") is not None:
        test_count = _int_attr(root, "tests")
        failures = _int_attr(root, "failures")
        errors = _int_attr(root, "errors")
        skipped = _int_attr(root, "skipped")
        total_time = _float_attr(root, "time")
    else:
        test_count = sum(_int_attr(suite, "tests") for suite in suites)
        failures = sum(_int_attr(suite, "failures") for suite in suites)
        errors = sum(_int_attr(suite, "errors") for suite in suites)
        skipped = sum(_int_attr(suite, "skipped") for suite in suites)
        total_time = sum(_float_attr(suite, "time") for suite in suites)

    if total_time == 0 and test_cases:
        total_time = sum(_float_attr(test_case, "time") for test_case in test_cases)

    effective_tests = max(test_count, 1)
    return {
        "test_count": test_count,
        "test_failures": failures + errors,
        "test_errors": errors,
        "test_skipped": skipped,
        "test_duration": round(total_time, 6),
        "test_avg_duration": round(total_time / effective_tests, 6),
        "generated_at": datetime.now(UTC).isoformat(),
        "experiment_label": os.getenv("EXPERIMENT_LABEL", ""),
        "cache_mode": os.getenv("CACHE_MODE", ""),
        "extra_test_cases": os.getenv("EXTRA_TEST_CASES", ""),
        "slow_test_seconds": os.getenv("SLOW_TEST_SECONDS", ""),
        "force_test_failure": os.getenv("FORCE_TEST_FAILURE", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Resume um arquivo JUnit XML do pytest.")
    parser.add_argument("junit_xml", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/test-summary.json"))
    args = parser.parse_args()

    summary = summarize(args.junit_xml)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
