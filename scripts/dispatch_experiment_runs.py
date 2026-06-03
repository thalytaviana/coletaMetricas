from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://api.github.com"


def _dispatch(
    repo: str,
    workflow: str,
    token: str,
    ref: str,
    inputs: dict[str, str],
    dry_run: bool,
) -> None:
    payload = json.dumps({"ref": ref, "inputs": inputs}).encode("utf-8")
    url = f"{API_BASE}/repos/{repo}/actions/workflows/{urllib.parse.quote(workflow)}/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "coleta-metricas-ci-experiment",
    }

    if dry_run:
        print(json.dumps({"url": url, "payload": json.loads(payload)}, indent=2))
        return

    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status not in {204, 201}:
            raise RuntimeError(f"GitHub retornou status inesperado: {response.status}")


def _inputs_from_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "experiment_label": row["variation"],
        "cache_mode": row["cache_mode"],
        "execution_mode": row["execution_mode"],
        "extra_test_cases": row["extra_test_cases"],
        "slow_test_seconds": row["slow_test_seconds"],
        "force_test_failure": row["force_test_failure"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dispara as execucoes planejadas no GitHub Actions.",
    )
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--workflow", default="ci.yml")
    parser.add_argument("--ref", default="main")
    parser.add_argument("--plan", type=Path, default=Path("data/experiment_plan.csv"))
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN"))
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.repo:
        raise SystemExit("Informe --repo DONO/REPO ou defina GITHUB_REPOSITORY.")
    if not args.token and not args.dry_run:
        raise SystemExit("Informe --token ou defina GITHUB_TOKEN/GH_TOKEN.")

    with args.plan.open(encoding="utf-8", newline="") as plan_file:
        rows = list(csv.DictReader(plan_file))

    for row in rows:
        inputs = _inputs_from_row(row)
        print(f"Disparando run {row['run_index']}: {row['variation']}")
        _dispatch(args.repo, args.workflow, args.token or "", args.ref, inputs, args.dry_run)
        if not args.dry_run:
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
