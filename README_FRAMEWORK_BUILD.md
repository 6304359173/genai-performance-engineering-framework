# AI Performance Framework — Integrated Pipeline Build

This update adds a separate, safer multi-phase k6 workflow while preserving the existing
`agent/orchestrator.py` and existing project modules.

## What this build adds

- One generic k6 scenario script driven by environment variables.
- A central JSON profile for the baseline/load/stress/spike/soak phases and SLA gates.
- Sequential execution: the next selected phase starts only after the current phase passes.
- Stops at the first failed or errored phase.
- Saves a raw k6 summary, per-phase result JSON, and consolidated JSON/Markdown reports.
- Checks response-time P95, HTTP request rate, HTTP error rate, check success rate, and dropped iterations.
- Explicit `--allow-intensive` guard for load/stress/spike/soak.
- Unit tests for metric extraction, gate decisions, phase ordering, and intensive-test safety.

## Important measurement distinction

The k6 `http_reqs.rate` metric is **HTTP requests per second**, not business transactions per second.
Do not call it business TPS unless transaction boundaries and business transaction metrics are instrumented.

## Run from the project root (Windows CMD)

First, verify the app responds:

```cmd
curl http://localhost:3002/health
```

Run only the 30-second baseline (default; does not require an intensive-test flag):

```cmd
python agent\pipeline_orchestrator.py
```

Run baseline and load phases sequentially:

```cmd
python agent\pipeline_orchestrator.py --phases baseline,load --allow-intensive
```

Run the complete sequence (baseline → load → stress → spike → soak):

```cmd
python agent\pipeline_orchestrator.py --phases baseline,load,stress,spike,soak --allow-intensive
```

The intensive command can generate higher traffic and run for several minutes. Only use it
against an authorized test environment. The pipeline stops at the first failed gate.

Override the target URL if required:

```cmd
python agent\pipeline_orchestrator.py --base-url http://localhost:3002/products
```

Run the unit tests without launching k6:

```cmd
python -m unittest tests.test_pipeline_orchestrator -v
```

## Configuration

Edit `config\performance_profile.json` to change:
- application/release metadata
- base URL
- P95 limit
- maximum HTTP error rate
- minimum check-success rate
- maximum dropped iterations
- per-phase arrival rate, duration, and gate rate

The profile preserves the existing baseline target of 10 HTTP requests/second and P95 limit of
2,000 ms. The load/stress/spike/soak rates are starter defaults, not universal production targets.
Adjust them to your workload model and environment capacity before running.

## Reports

Each session writes to `reports\`:
- `<session>-<phase>-k6-summary.json` — raw k6 summary export
- `<session>-<phase>-result.json` — extracted metrics and gate result
- `<session>-pipeline-report.json` — consolidated machine-readable report
- `<session>-pipeline-report.md` — consolidated engineering report

## Current integration boundaries

This pipeline executes k6 only. The repository also contains JMeter, analyzer, MCP, Ollama,
Kubernetes and Jenkins assets, but those are not automatically chained into this new pipeline yet.
The current Jenkinsfile is machine-specific and runs a separate JMeter/MCP workflow. Those
integrations should be connected and tested as the next implementation milestone rather than
being described as already integrated.

The legacy `agent\orchestrator.py` is preserved unchanged. Use `agent\pipeline_orchestrator.py`
for the new multi-phase k6 workflow.
