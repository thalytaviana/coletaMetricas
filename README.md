# coletaMetricas

Experimento pratico para instrumentar um pipeline CI/CD no GitHub Actions, coletar metricas reais de execucao, gerar graficos e produzir um relatorio tecnico.

Repositorio GitHub: https://github.com/thalytaviana/coletaMetricas

## Estrutura

- `.github/workflows/ci.yml`: pipeline com instalacao de dependencias, cache opcional, lint, testes, resumo de metricas e upload de artefatos.
- `src/coleta_metricas/`: aplicacao Python simples usada pelos testes.
- `tests/`: testes automatizados com variacoes controladas por variaveis de ambiente.
- `scripts/summarize_pytest.py`: resume o JUnit XML do pytest em JSON.
- `scripts/collect_metrics.py`: coleta metricas reais pela API do GitHub Actions e gera CSV.
- `scripts/generate_charts.py`: gera os quatro graficos obrigatorios a partir do CSV.
- `scripts/dispatch_experiment_runs.py`: dispara as 12 execucoes planejadas via `workflow_dispatch`.
- `data/experiment_plan.csv`: plano sugerido para as 12 execucoes.
- `docs/relatorio.md`: relatorio tecnico em Markdown, com secoes obrigatorias.

## Como executar localmente

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest --junitxml=reports/junit.xml
python scripts/summarize_pytest.py reports/junit.xml --output reports/test-summary.json
```

Para simular variacoes localmente:

```powershell
$env:EXTRA_TEST_CASES="30"
$env:SLOW_TEST_SECONDS="2"
$env:FORCE_TEST_FAILURE="false"
python -m pytest --junitxml=reports/junit.xml
```

## Como executar o experimento no GitHub

1. Faca commit e push deste projeto para `main`.
2. Confirme que `.github/workflows/ci.yml` aparece na aba **Actions**.
3. Dispare as 12 execucoes usando o plano em `data/experiment_plan.csv`.
4. Inclua variacoes com cache ligado/desligado, teste lento, aumento artificial de testes, falha controlada e modo paralelo/sequencial.

Ha duas formas de executar as variacoes:

- Por commit: altere `experiment.env`, faca commit e push. O workflow `push` le essa configuracao.
- Por API: use `workflow_dispatch` com `scripts/dispatch_experiment_runs.py`.

```powershell
$env:GITHUB_TOKEN="ghp_token_com_actions_write"
python scripts/dispatch_experiment_runs.py --repo thalytaviana/coletaMetricas --workflow ci.yml --ref main
```

Depois que as execucoes terminarem, gere a base de dados:

```powershell
$env:GITHUB_TOKEN="ghp_token_com_actions_read"
python scripts/collect_metrics.py --repo thalytaviana/coletaMetricas --workflow ci.yml --limit 30 --output data/pipeline_metrics.csv
```

Gere os graficos:

```powershell
python scripts/generate_charts.py --input data/pipeline_metrics.csv --output-dir charts
```

Atualize `docs/relatorio.md` com os IDs reais, links das execucoes e analise final.

## Artefatos do pipeline

Cada execucao publica:

- `test-summary-<run_id>`: contem `junit.xml` e `test-summary.json`.
- `pipeline-context-<run_id>`: contem metadados da execucao, variacoes usadas e resultados dos jobs.
- `pipeline-results-<run_id>`: pacote compactado com os relatorios gerados.

## Metricas coletadas

O coletor gera linhas por job com, no minimo:

```text
run_id,commit_sha,commit_message,status,workflow_duration,job_name,job_duration,test_count,test_failures,timestamp
```

Tambem sao incluidos campos auxiliares como numero da execucao, URL, duracao media dos testes, configuracao de cache, modo de execucao e duracao das etapas em JSON.
