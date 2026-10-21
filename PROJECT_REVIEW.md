# Project Review — AI Performance Framework

Review basis: uploaded `ai-perf-framework.zip`. The `.env` file was deliberately not opened or copied into the updated bundle.

## What is genuinely present

- A k6 baseline script and an existing Python orchestrator that executes it and applies a Phase Gate.
- A standalone JMeter executor and a JMeter test plan.
- A sizeable JTL analyzer with SLA and steady-state/business-throughput logic.
- An Ollama/Qwen3 client and RCA prompt/report artifacts.
- MCP server/client code for exposing performance evidence.
- Kubernetes manifests and a Jenkins pipeline.

## Material integration gaps found

1. **The existing PASS message is not actual phase progression.** In `agent/orchestrator.py`, a PASS prints “Proceed to next phase” and then the method ends. No next phase is launched.
2. **The existing main orchestrator runs only k6.** Non-k6 engines raise `NotImplementedError`, despite a separate JMeter executor being present.
3. **The Jenkins workflow is a separate path.** It runs JMeter/MCP and contains machine-specific Windows paths, a local kubeconfig, ports, and tool paths. It is not calling the k6 Phase Gate orchestrator.
4. **JTL path mismatch:** `python-engine/analyzer.py` reads `results/generated_tps_results.jtl`, while the Jenkinsfile configures `scripts\results.jtl`. Unless separately overridden, the analyzer can analyze a different/stale file from the one Jenkins just generated.
5. **JMeter plan safety/validity needs review before automated execution.** The uploaded `scripts/ai_perf_test.jmx` contains a Debug Sampler and an Open Model Thread Group schedule containing `rate(100/sec)` and `rate(500/sec)`. Do not run that plan against a shared or production target without reviewing and deliberately enabling the intended workload.
6. **HTTP request rate vs business TPS:** the k6 baseline reports `http_reqs.rate`; that is HTTP requests/second. It is not proof of business transactions/second.
7. **AI RCA is not equivalent to telemetry-backed root-cause confirmation.** The local LLM can summarize evidence, but server/GC/database/network/APM evidence must be connected before declaring a root cause.

## Changes included in this build

- Added `agent/pipeline_orchestrator.py` as a distinct multi-phase k6 pipeline.
- Added `tests/scenario.js`, parameterized by phase rate/duration/URL.
- Added `config/performance_profile.json` for baseline/load/stress/spike/soak and the gate thresholds.
- Added a sequential stop-on-failure flow, per-phase artifacts, and consolidated JSON/Markdown reporting.
- Added an explicit `--allow-intensive` guard for load/stress/spike/soak.
- Added five unit tests; all five passed in the build environment.
- Added `README_FRAMEWORK_BUILD.md` with run instructions.
- Kept the existing `agent/orchestrator.py` and other original code intact.
- Excluded `.env`, `node_modules`, Python caches, and transient JTL/log artifacts from the updated ZIP.

## Recommended implementation order after this build

1. Run the new pipeline's unit tests on the user's Windows machine.
2. Run baseline with the new pipeline and compare its report to the existing successful run.
3. Clean and validate the JMeter plan; standardize the JTL path and integrate the JMeter adapter behind the same phase contract.
4. Make Jenkins call one canonical orchestrator and remove hardcoded workstation paths in favor of Jenkins parameters/credentials.
5. Connect telemetry collection (Kubernetes plus APM/DB) to each test session and include timestamp-aligned evidence in RCA.
6. Validate local Qwen3 RCA with timeouts/failure handling, then generate the final report and retest plan.
7. Add historical comparison/trend analysis and enforce release gates in CI.

## Security note

The uploaded archive contained `ai-engine/.env`. It was excluded from the updated bundle. If it contains a real credential, revoke/rotate that credential and ensure `.env` is ignored by Git; do not upload it again.
