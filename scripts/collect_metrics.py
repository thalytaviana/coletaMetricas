from __future__ import annotations

import argparse
import csv
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

API_BASE = "https://api.github.com"

FIELDNAMES = [
    "run_id",
    "run_number",
    "commit_sha",
    "commit_message",
    "status",
    "workflow_duration",
    "job_name",
    "job_status",
    "job_duration",
    "test_count",
    "test_failures",
    "test_duration",
    "test_avg_duration",
    "timestamp",
    "html_url",
    "experiment_label",
    "cache_mode",
    "execution_mode",
    "extra_test_cases",
    "slow_test_seconds",
    "force_test_failure",
    "step_durations_json",
]


class _NoAuthRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N803
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None

        original_host = urllib.parse.urlparse(req.full_url).netloc
        redirected_host = urllib.parse.urlparse(newurl).netloc
        if original_host != redirected_host:
            redirected.headers.pop("Authorization", None)
            redirected.unredirected_hdrs.pop("Authorization", None)
        return redirected


_OPENER = urllib.request.build_opener(_NoAuthRedirectHandler)


def _request_bytes(url: str, token: str | None, method: str = "GET") -> bytes:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "coleta-metricas-ci-experiment",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers, method=method)
    with _OPENER.open(request, timeout=30) as response:
        return response.read()


def _get_json(path: str, token: str | None, params: dict[str, object] | None = None) -> Any:
    url = path if path.startswith("http") else f"{API_BASE}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    return json.loads(_request_bytes(url, token).decode("utf-8"))


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _duration_seconds(start: str | None, end: str | None) -> float:
    started_at = _parse_datetime(start)
    completed_at = _parse_datetime(end)
    if not started_at or not completed_at:
        return 0.0
    return round((completed_at - started_at).total_seconds(), 3)


def _first_line(message: str | None) -> str:
    if not message:
        return ""
    return message.strip().splitlines()[0]


def _safe_int(value: object) -> int | str:
    if value in (None, ""):
        return ""
    try:
        return int(str(value))
    except ValueError:
        return ""


def _safe_float(value: object) -> float | str:
    if value in (None, ""):
        return ""
    try:
        return round(float(str(value)), 6)
    except ValueError:
        return ""


def _extract_artifact_jsons(artifact: dict[str, Any], token: str | None) -> dict[str, Any]:
    try:
        data = _request_bytes(artifact["archive_download_url"], token)
    except (KeyError, urllib.error.HTTPError, urllib.error.URLError):
        return {}

    extracted: dict[str, Any] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member_name in archive.namelist():
            filename = Path(member_name).name
            if filename not in {"test-summary.json", "workflow-context.json"}:
                continue
            with archive.open(member_name) as member:
                extracted[filename] = json.loads(member.read().decode("utf-8"))
    return extracted


def _artifact_context(repo: str, run_id: int, token: str | None) -> dict[str, Any]:
    artifacts = _get_json(
        f"/repos/{repo}/actions/runs/{run_id}/artifacts",
        token,
        {"per_page": 100},
    ).get("artifacts", [])

    context: dict[str, Any] = {}
    for artifact in artifacts:
        name = artifact.get("name", "")
        if not name.startswith(("test-summary-", "pipeline-context-")):
            continue
        extracted = _extract_artifact_jsons(artifact, token)
        if "test-summary.json" in extracted:
            context["test_summary"] = extracted["test-summary.json"]
        if "workflow-context.json" in extracted:
            context["workflow_context"] = extracted["workflow-context.json"]
    return context


def _list_runs(repo: str, workflow: str, token: str | None, limit: int) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    page = 1
    while len(runs) < limit:
        payload = _get_json(
            f"/repos/{repo}/actions/workflows/{workflow}/runs",
            token,
            {"per_page": min(100, limit), "page": page},
        )
        page_runs = payload.get("workflow_runs", [])
        if not page_runs:
            break
        runs.extend(page_runs)
        page += 1
    return runs[:limit]


def _list_jobs(repo: str, run_id: int, token: str | None) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = _get_json(
            f"/repos/{repo}/actions/runs/{run_id}/jobs",
            token,
            {"per_page": 100, "page": page},
        )
        page_jobs = payload.get("jobs", [])
        if not page_jobs:
            break
        jobs.extend(page_jobs)
        page += 1
    return jobs


def collect(repo: str, workflow: str, token: str | None, limit: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    runs = _list_runs(repo, workflow, token, limit)

    for run in runs:
        run_id = int(run["id"])
        commit = run.get("head_commit") or {}
        artifact_context = _artifact_context(repo, run_id, token)
        test_summary = artifact_context.get("test_summary", {})
        workflow_context = artifact_context.get("workflow_context", {})
        workflow_duration = _duration_seconds(
            run.get("run_started_at") or run.get("created_at"),
            run.get("updated_at"),
        )

        jobs = _list_jobs(repo, run_id, token)
        if not jobs:
            jobs = [{"name": "", "conclusion": "", "started_at": None, "completed_at": None}]

        for job in jobs:
            steps = {}
            for step in job.get("steps", []):
                steps[step.get("name", "")] = _duration_seconds(
                    step.get("started_at"),
                    step.get("completed_at"),
                )

            rows.append(
                {
                    "run_id": run_id,
                    "run_number": run.get("run_number", ""),
                    "commit_sha": run.get("head_sha", ""),
                    "commit_message": _first_line(commit.get("message")),
                    "status": run.get("conclusion") or run.get("status", ""),
                    "workflow_duration": workflow_duration,
                    "job_name": job.get("name", ""),
                    "job_status": job.get("conclusion") or job.get("status", ""),
                    "job_duration": _duration_seconds(
                        job.get("started_at"),
                        job.get("completed_at"),
                    ),
                    "test_count": _safe_int(test_summary.get("test_count")),
                    "test_failures": _safe_int(test_summary.get("test_failures")),
                    "test_duration": _safe_float(test_summary.get("test_duration")),
                    "test_avg_duration": _safe_float(test_summary.get("test_avg_duration")),
                    "timestamp": run.get("run_started_at") or run.get("created_at", ""),
                    "html_url": run.get("html_url", ""),
                    "experiment_label": workflow_context.get(
                        "experiment_label",
                        test_summary.get("experiment_label", ""),
                    ),
                    "cache_mode": workflow_context.get(
                        "cache_mode",
                        test_summary.get("cache_mode", ""),
                    ),
                    "execution_mode": workflow_context.get("execution_mode", ""),
                    "extra_test_cases": workflow_context.get(
                        "extra_test_cases",
                        test_summary.get("extra_test_cases", ""),
                    ),
                    "slow_test_seconds": workflow_context.get(
                        "slow_test_seconds",
                        test_summary.get("slow_test_seconds", ""),
                    ),
                    "force_test_failure": workflow_context.get(
                        "force_test_failure",
                        test_summary.get("force_test_failure", ""),
                    ),
                    "step_durations_json": json.dumps(steps, ensure_ascii=True),
                },
            )
    return rows


def write_csv(rows: list[dict[str, object]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta metricas reais do GitHub Actions.")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--workflow", default="ci.yml")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--output", type=Path, default=Path("data/pipeline_metrics.csv"))
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN"))
    args = parser.parse_args()

    if not args.repo:
        raise SystemExit("Informe --repo DONO/REPO ou defina GITHUB_REPOSITORY.")

    rows = collect(args.repo, args.workflow, args.token, args.limit)
    write_csv(rows, args.output)
    print(f"{len(rows)} linhas gravadas em {args.output}")


if __name__ == "__main__":
    main()
