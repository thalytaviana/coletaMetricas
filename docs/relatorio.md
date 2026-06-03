# Relatorio tecnico: metricas de CI/CD com GitHub Actions

## Repositorio e workflow

- Repositorio GitHub: https://github.com/thalytaviana/coletaMetricas
- Workflow YAML: https://github.com/thalytaviana/coletaMetricas/blob/main/.github/workflows/ci.yml
- Configuracao de variacao por commit: `experiment.env`
- Script de coleta: `scripts/collect_metrics.py`
- Base gerada: `data/pipeline_metrics.csv`
- Graficos: `charts/`

## Hipotese inicial

A hipotese inicial era que o cache reduziria principalmente o tempo de instalacao de dependencias, enquanto aumento de testes e testes lentos afetariam mais diretamente o job de testes. Tambem se esperava que o paralelismo reduzisse o tempo total quando `lint` e `tests` tivessem duracoes parecidas.

## Commits usados

As 12 execucoes principais foram disparadas por `workflow_dispatch` em `main` usando o commit `e99594d5a6b9f16247d11d1581a2e5249da768c3` (`Support experiment config from commits`). O commit anterior `457c7ff` (`Add GitHub Actions metrics experiment`) tambem gerou uma execucao inicial de validacao, mas nao entrou nos graficos finais.

## Variacoes executadas

| Execucao | Variacao | Run ID real | Commit | Status | Link |
| --- | --- | --- | --- | --- | --- |
| 1 | baseline_verde | 26889135368 | e99594d | success | https://github.com/thalytaviana/coletaMetricas/actions/runs/26889135368 |
| 2 | baseline_repetido_cache_quente | 26889140297 | e99594d | success | https://github.com/thalytaviana/coletaMetricas/actions/runs/26889140297 |
| 3 | cache_desligado | 26889144720 | e99594d | success | https://github.com/thalytaviana/coletaMetricas/actions/runs/26889144720 |
| 4 | mais_testes | 26889149145 | e99594d | success | https://github.com/thalytaviana/coletaMetricas/actions/runs/26889149145 |
| 5 | muitos_testes | 26889153416 | e99594d | success | https://github.com/thalytaviana/coletaMetricas/actions/runs/26889153416 |
| 6 | teste_lento_1s | 26889157963 | e99594d | success | https://github.com/thalytaviana/coletaMetricas/actions/runs/26889157963 |
| 7 | teste_lento_3s | 26889162399 | e99594d | success | https://github.com/thalytaviana/coletaMetricas/actions/runs/26889162399 |
| 8 | falha_controlada | 26889166894 | e99594d | failure | https://github.com/thalytaviana/coletaMetricas/actions/runs/26889166894 |
| 9 | recuperacao_pos_falha | 26889171133 | e99594d | success | https://github.com/thalytaviana/coletaMetricas/actions/runs/26889171133 |
| 10 | cache_desligado_com_muitos_testes | 26889176306 | e99594d | success | https://github.com/thalytaviana/coletaMetricas/actions/runs/26889176306 |
| 11 | paralelo_com_muitos_testes | 26889181073 | e99594d | success | https://github.com/thalytaviana/coletaMetricas/actions/runs/26889181073 |
| 12 | sequencial_com_muitos_testes | 26889185502 | e99594d | success | https://github.com/thalytaviana/coletaMetricas/actions/runs/26889185502 |

## Evidencias reais

Os links acima apontam para as execucoes reais do GitHub Actions. Os mesmos links tambem estao na coluna `html_url` da base `data/pipeline_metrics.csv`. Cada execucao publicou artefatos `test-summary-<run_id>`, `pipeline-context-<run_id>` e `pipeline-results-<run_id>`.

## Graficos

![Tempo total do pipeline por execucao](../charts/01_pipeline_duration_by_run.png)

![Tempo por job](../charts/02_job_duration_by_run.png)

![Taxa de sucesso e falha](../charts/03_success_failure_rate.png)

![Quantidade de testes x duracao do pipeline](../charts/04_tests_vs_pipeline_duration.png)

## Resultados numericos principais

- Total de execucoes analisadas: 12.
- Status: 11 sucessos e 1 falha controlada.
- Duracao total mediana: 50,5 s.
- Menor duracao total: 45 s (`recuperacao_pos_falha`).
- Maior duracao total: 83 s (`sequencial_com_muitos_testes`).
- Maior quantidade de testes: 131 (`muitos_testes`).
- Falhas de teste: 1, somente em `falha_controlada`.

## Analise

### Qual etapa mais contribuiu para o tempo total do pipeline?

Os jobs `tests-parallel` e `lint` foram os maiores contribuintes. Considerando os jobs observados, `tests-parallel` teve media de 23,4 s incluindo a execucao sequencial em que ele ficou `skipped`; nas execucoes paralelas em que rodou, ficou em torno de 25 s. O job `lint` teve media de 23,1 s. Dentro desses jobs, a etapa que mais consumiu tempo foi `Install dependencies`, geralmente entre 14 s e 16 s, enquanto `Run pytest` ficou entre 0 s e 3 s.

### Houve diferenca significativa entre execucoes com e sem cache?

Nao houve evidencia forte de ganho com cache. As execucoes sem cache tiveram media de 50,5 s, enquanto as execucoes com cache tiveram media de 53,4 s e mediana de 50,5 s. O resultado sugere que, neste projeto pequeno, o tempo de restaurar cache e a variabilidade do runner foram comparaveis ao tempo economizado na instalacao.

### O paralelismo reduziu o tempo total? Em que condicoes?

Sim. A comparacao direta entre `paralelo_com_muitos_testes` e `sequencial_com_muitos_testes` mostra reducao de 83 s para 51 s, uma economia de 32 s. O paralelismo ajudou porque `lint` e `tests` tinham duracoes semelhantes, aproximadamente 22 s a 27 s, permitindo sobreposicao real entre os jobs.

### Quais falhas foram mais frequentes?

Houve apenas uma falha, criada propositalmente por `FORCE_TEST_FAILURE=true` na execucao `falha_controlada`. Portanto, a falha mais frequente foi falha de teste automatizado. Nao houve falhas observadas em lint, instalacao de dependencias, upload de artefatos ou coleta de contexto.

### O pipeline fornece feedback rapido o suficiente para o desenvolvedor?

Para um projeto pequeno, sim: a mediana de 50,5 s fornece feedback em cerca de um minuto. Entretanto, o resultado tambem mostra que o feedback e dominado por overhead de ambiente e instalacao, nao pelo tempo real dos testes. Em um projeto maior, esse desenho precisaria de otimizacoes para continuar rapido.

### Que melhorias poderiam ser feitas no pipeline?

As melhorias mais promissoras seriam reduzir instalacoes duplicadas entre `lint` e `tests`, usar cache nativo do `actions/setup-python`, separar dependencias de lint das dependencias de teste, publicar um resumo no GitHub Step Summary e medir cache hit/miss explicitamente. Outra melhoria seria separar testes lentos em uma suite propria para preservar feedback rapido nos testes comuns.

### Quais limitacoes existem nos dados coletados?

A amostra e pequena, com apenas 12 execucoes principais. As execucoes ocorreram em runners hospedados pelo GitHub, sujeitos a variabilidade externa. Todas as variacoes por `workflow_dispatch` usaram o mesmo commit, entao a comparacao isola configuracao do pipeline, mas nao mede impacto de mudancas reais de codigo. Alem disso, o projeto e pequeno e o tempo de testes e muito baixo em relacao ao overhead do ambiente.

### Como essa analise poderia apoiar decisoes de engenharia?

A analise mostra onde vale investir primeiro. Neste caso, melhorar instalacao/cache e manter `lint` e `tests` paralelos tende a trazer mais retorno do que otimizar testes individuais. Tambem ajuda a justificar separacao de testes lentos e a definir uma meta de feedback, por exemplo manter o pipeline abaixo de 1 minuto em cenarios comuns.

## Resultados inesperados

1. **Cache desligado nao foi claramente pior.** A execucao `cache_desligado` levou 47 s, menor que as duas primeiras execucoes com cache, de 54 s e 49 s. Isso foi inesperado porque a hipotese inicial previa ganho evidente com cache. Uma possivel causa e que o projeto tem poucas dependencias e o custo de restaurar cache se aproxima do custo de instalar tudo novamente.
2. **Aumento de testes quase nao aumentou o tempo total.** `muitos_testes` executou 131 testes e durou 48 s, menos que o baseline de 54 s. Isso indica que, nesta escala, a duracao total foi dominada pelo setup do runner e instalacao de dependencias, enquanto o tempo de pytest ainda era pequeno.

## Comparacao entre hipotese e resultado observado

A hipotese sobre paralelismo foi confirmada: o modo paralelo reduziu o tempo total de 83 s para 51 s quando comparado ao modo sequencial com a mesma quantidade de testes. A hipotese sobre cache nao foi confirmada nos dados: nao houve diferenca significativa entre execucoes com e sem cache. A hipotese sobre testes lentos apareceu nos dados de `test_duration`, que subiu para 1,041 s e 3,035 s nos cenarios lentos, mas esse aumento nao se refletiu fortemente na duracao total do workflow por causa do overhead fixo do pipeline.

## Como reproduzir

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

$env:GITHUB_TOKEN="ghp_token_com_actions_write"
python scripts/dispatch_experiment_runs.py --repo thalytaviana/coletaMetricas --workflow ci.yml --ref main

$env:GITHUB_TOKEN="ghp_token_com_actions_read"
python scripts/collect_metrics.py --repo thalytaviana/coletaMetricas --workflow ci.yml --limit 12 --output data/pipeline_metrics.csv
python scripts/generate_charts.py --input data/pipeline_metrics.csv --output-dir charts
```
