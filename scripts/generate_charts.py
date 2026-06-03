from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


def _run_frame(data: pd.DataFrame) -> pd.DataFrame:
    runs = data.drop_duplicates("run_id").copy()
    runs["timestamp"] = pd.to_datetime(runs["timestamp"], errors="coerce")
    runs = runs.sort_values(["timestamp", "run_number"])
    runs["run_label"] = runs["run_number"].fillna(runs["run_id"]).astype(str)
    runs["workflow_duration"] = pd.to_numeric(runs["workflow_duration"], errors="coerce")
    runs["test_count"] = pd.to_numeric(runs["test_count"], errors="coerce")
    return runs


def _save_pipeline_duration(runs: pd.DataFrame, output_dir: Path) -> None:
    fig, axis = plt.subplots(figsize=(11, 5))
    axis.plot(runs["run_label"], runs["workflow_duration"], marker="o", color="#2563eb")
    axis.set_title("Tempo total do pipeline por execucao")
    axis.set_xlabel("Execucao")
    axis.set_ylabel("Duracao (s)")
    axis.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "01_pipeline_duration_by_run.png", dpi=160)
    plt.close(fig)


def _save_job_duration(data: pd.DataFrame, output_dir: Path) -> None:
    jobs = data.copy()
    jobs["job_duration"] = pd.to_numeric(jobs["job_duration"], errors="coerce")
    jobs["run_label"] = jobs["run_number"].fillna(jobs["run_id"]).astype(str)
    pivot = jobs.pivot_table(
        index="run_label",
        columns="job_name",
        values="job_duration",
        aggfunc="max",
    ).fillna(0)

    fig, axis = plt.subplots(figsize=(11, 5))
    pivot.plot(kind="bar", stacked=True, ax=axis, width=0.8)
    axis.set_title("Tempo por job")
    axis.set_xlabel("Execucao")
    axis.set_ylabel("Duracao (s)")
    axis.legend(title="Job", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_dir / "02_job_duration_by_run.png", dpi=160)
    plt.close(fig)


def _save_status_rate(runs: pd.DataFrame, output_dir: Path) -> None:
    counts = runs["status"].fillna("unknown").value_counts().sort_index()
    percentages = (counts / counts.sum()) * 100

    fig, axis = plt.subplots(figsize=(7, 5))
    palette = ["#16a34a", "#dc2626", "#64748b"]
    bars = axis.bar(counts.index, percentages, color=palette[: len(counts)])
    axis.set_title("Taxa de sucesso e falha")
    axis.set_xlabel("Status")
    axis.set_ylabel("Percentual de execucoes")
    axis.set_ylim(0, max(100, percentages.max() + 10))
    for bar, value in zip(bars, percentages, strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{value:.1f}%",
            ha="center",
        )
    fig.tight_layout()
    fig.savefig(output_dir / "03_success_failure_rate.png", dpi=160)
    plt.close(fig)


def _save_tests_vs_duration(runs: pd.DataFrame, output_dir: Path) -> None:
    color_by_status = {
        "success": "#16a34a",
        "failure": "#dc2626",
        "cancelled": "#64748b",
        "unknown": "#64748b",
    }
    colors = runs["status"].fillna("unknown").map(
        lambda status: color_by_status.get(status, "#64748b"),
    )

    fig, axis = plt.subplots(figsize=(8, 5))
    axis.scatter(runs["test_count"], runs["workflow_duration"], s=80, c=colors, alpha=0.85)
    for _, row in runs.iterrows():
        axis.annotate(
            str(row["run_label"]),
            (row["test_count"], row["workflow_duration"]),
            xytext=(5, 5),
            textcoords="offset points",
        )
    axis.set_title("Quantidade de testes x duracao do pipeline")
    axis.set_xlabel("Quantidade de testes")
    axis.set_ylabel("Duracao total (s)")
    axis.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "04_tests_vs_pipeline_duration.png", dpi=160)
    plt.close(fig)


def generate(input_csv: Path, output_dir: Path) -> list[Path]:
    data = pd.read_csv(input_csv)
    if data.empty:
        raise SystemExit("CSV vazio: colete execucoes reais antes de gerar os graficos.")

    output_dir.mkdir(parents=True, exist_ok=True)
    runs = _run_frame(data)
    _save_pipeline_duration(runs, output_dir)
    _save_job_duration(data, output_dir)
    _save_status_rate(runs, output_dir)
    _save_tests_vs_duration(runs, output_dir)
    return sorted(output_dir.glob("*.png"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera graficos do experimento CI/CD.")
    parser.add_argument("--input", type=Path, default=Path("data/pipeline_metrics.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("charts"))
    args = parser.parse_args()

    charts = generate(args.input, args.output_dir)
    for chart in charts:
        print(chart)


if __name__ == "__main__":
    main()
