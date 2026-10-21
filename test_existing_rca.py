import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SESSION = "PERF-20261019-182451"

summary_path = ROOT / "reports" / f"{SESSION}-summary.json"
report_path = ROOT / "reports" / f"{SESSION}-rca-diagnostic.md"
ai_engine = ROOT / "ai-engine"

if not summary_path.is_file():
    raise FileNotFoundError(f"Metrics file not found: {summary_path}")

with summary_path.open("r", encoding="utf-8") as f:
    summary = json.load(f)

metrics = summary.get("metrics", {})

evidence = {
    "session_id": SESSION,
    "application": "AI Order Service",
    "release": "5.2",
    "test_type": "baseline",
    "target_http_request_rate_per_second": 11,
    "target_p95_ms": 2000,
    "target_error_rate_percent": 1,
    "raw_k6_metrics": {
        name: metrics.get(name)
        for name in [
            "http_req_duration",
            "http_reqs",
            "http_req_failed",
            "checks",
            "iterations",
            "dropped_iterations",
        ]
    },
}

prompt = f"""
You are a Senior Performance Engineer.

Analyze this saved performance-test evidence. Do not rerun the test.

Produce these sections:
1. Executive Summary
2. Measured Facts
3. SLA and Phase Gate Assessment
4. Potential Causes (label as hypotheses)
5. Additional Telemetry Required
6. Prioritized Recommendations
7. Controlled Retest Strategy
8. Final Engineering Conclusion

Rules:
- Use only the supplied evidence.
- Preserve and explicitly flag conflicting or inconsistent metric fields.
- Do not invent a confirmed root cause.
- Distinguish HTTP requests per second from business TPS.
- The historical target rate for this failed session was 11 requests/sec.
- State that remediation and retesting have not been performed.
- Provide a complete report, not just a summary.

Saved evidence:
{json.dumps(evidence, indent=2)}
"""

if str(ai_engine) not in sys.path:
    sys.path.insert(0, str(ai_engine))

from llm_client import is_llm_configured, generate_ai_rca

if not is_llm_configured():
    raise RuntimeError(
        "Ollama/Qwen3 is unavailable. Start Ollama and retry."
    )

print("Generating diagnostic RCA from saved metrics...")
result = generate_ai_rca(prompt)

if not isinstance(result, str) or not result.strip():
    raise RuntimeError("Qwen3 returned an empty report.")

report_path.write_text(
    "# RCA Diagnostic Report\n\n"
    f"- Session: {SESSION}\n"
    "- Source: Existing saved k6 summary\n"
    "- Test rerun: No\n\n"
    "---\n\n"
    + result.strip()
    + "\n",
    encoding="utf-8",
)

print("\nDiagnostic RCA generated successfully.")
print(f"Report: {report_path}")
print(f"Report size: {report_path.stat().st_size} bytes")