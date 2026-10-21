
import glob
import json
import os
from datetime import datetime

REPORT_DIR = "reports"
OUTPUT_JSON = os.path.join(REPORT_DIR, "consolidated-performance-report.json")
OUTPUT_MD = os.path.join(REPORT_DIR, "consolidated-performance-report.md")

EXPECTED_PHASES = ["baseline", "load", "stress", "spike", "soak"]

reports = []
for filename in sorted(glob.glob(os.path.join(REPORT_DIR, "*-pipeline-report.json"))):
    if os.path.basename(filename) == os.path.basename(OUTPUT_JSON):
        continue

    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)

    reports.append(data)

if not reports:
    raise SystemExit("ERROR: No pipeline report JSON files found.")

phase_results = {}
for report in reports:
    for phase in report.get("phases", []):
        name = phase.get("phase")
        if name not in EXPECTED_PHASES:
            continue

        # Keep the most recent recorded result for each phase.
        started_at = phase.get("started_at", "")
        previous = phase_results.get(name)
        if previous is None or started_at > previous.get("started_at", ""):
            phase_results[name] = {
                **phase,
                "source_session": report.get("session_id", "unknown"),
            }

missing = [p for p in EXPECTED_PHASES if p not in phase_results]
overall_status = (
    "INCOMPLETE" if missing
    else "PASS" if all(
        phase_results[p].get("status") == "PASS"
        for p in EXPECTED_PHASES
    )
    else "FAIL"
)

consolidated = {
    "application": reports[-1].get("application", "Unknown"),
    "release": reports[-1].get("release", "Unknown"),
    "generated_at": datetime.now().astimezone().isoformat(),
    "overall_status": overall_status,
    "expected_phases": EXPECTED_PHASES,
    "missing_phases": missing,
    "phases": [
        phase_results[p] for p in EXPECTED_PHASES
        if p in phase_results
    ],
    "source_sessions": [
        r.get("session_id", "unknown") for r in reports
    ],
    "interpretation_note": (
        "k6 reports HTTP requests per second, not business TPS. "
        "Results apply only to the tested endpoint, workload, "
        "duration, environment, and available telemetry."
    ),
}

with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
    json.dump(consolidated, file, indent=2)

lines = [
    "# Consolidated Performance Engineering Report",
    "",
    f"- Application: {consolidated['application']}",
    f"- Release: {consolidated['release']}",
    f"- Generated: {consolidated['generated_at']}",
    f"- Overall result: **{overall_status}**",
    "",
    "| Phase | Status | P95 (ms) | HTTP req/sec | HTTP errors (%) | Checks success | Dropped iterations | Source session |",
    "|---|---|---:|---:|---:|---:|---:|---|",
]

for p in consolidated["phases"]:
    m = p.get("metrics", {})
    lines.append(
        f"| {p.get('phase')} | {p.get('status')} "
        f"| {m.get('p95_ms', 'N/A')} "
        f"| {m.get('http_request_rate_per_sec', 'N/A')} "
        f"| {m.get('http_error_rate_percent', 'N/A')} "
        f"| {m.get('checks_rate', 0) * 100:.2f}% "
        f"| {m.get('dropped_iterations', 'N/A')} "
        f"| {p.get('source_session', 'unknown')} |"
    )

lines += ["", "## Gate details", ""]
for p in consolidated["phases"]:
    lines.append(f"### {p.get('phase')}: {p.get('status')}")
    checks = p.get("gate", {}).get("checks", {})
    if checks:
        for name, passed in checks.items():
            lines.append(f"- {name}: {'PASS' if passed else 'FAIL'}")
    else:
        lines.append("- Gate details unavailable in source report.")
    lines.append("")

if missing:
    lines.append("## Missing phases")
    lines.append("The following phases do not have recorded results: "
                 + ", ".join(missing) + ".")
    lines.append("")

lines += [
    "## Interpretation",
    "",
    consolidated["interpretation_note"],
    "",
    "A complete PASS requires all five expected phases to have a "
    "recorded PASS status. This report combines existing results; "
    "it does not rerun tests or prove production capacity.",
]

with open(OUTPUT_MD, "w", encoding="utf-8", newline="\n") as file:
    file.write("\n".join(lines) + "\n")

print("Consolidation complete.")
print("Overall status:", overall_status)
print("Phases found:", ", ".join(phase_results.keys()))
if missing:
    print("Missing phases:", ", ".join(missing))
print("Markdown report:", OUTPUT_MD)
print("JSON report:", OUTPUT_JSON)
