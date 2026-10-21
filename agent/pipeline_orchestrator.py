from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILE_FILE = ROOT / "config" / "performance_profile.json"
SCENARIO_FILE = ROOT / "tests" / "scenario.js"
REPORTS_DIR = ROOT / "reports"
PHASE_ORDER = ["baseline", "load", "stress", "spike", "soak"]


def load_profile(path: Path = PROFILE_FILE) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        profile = json.load(stream)
    for required in ("application", "release", "base_url", "sla", "phases"):
        if required not in profile:
            raise ValueError(f"Performance profile is missing '{required}'.")
    for phase in PHASE_ORDER:
        if phase not in profile["phases"]:
            raise ValueError(f"Performance profile is missing phase '{phase}'.")
    return profile


def validate_phases(phases: list[str], profile: dict[str, Any], allow_intensive: bool) -> None:
    if not phases:
        raise ValueError("Select at least one phase.")
    unknown = [phase for phase in phases if phase not in profile["phases"]]
    if unknown:
        raise ValueError(f"Unknown phase(s): {', '.join(unknown)}.")
    if len(set(phases)) != len(phases):
        raise ValueError("A phase cannot appear more than once in one run.")
    if phases != sorted(phases, key=PHASE_ORDER.index):
        raise ValueError("Phases must be in order: baseline, load, stress, spike, soak.")
    intensive = [p for p in phases if profile["phases"][p].get("intensive", False)]
    if intensive and not allow_intensive:
        raise ValueError(
            "Load/stress/spike/soak phases can generate sustained or elevated traffic. "
            "Re-run with --allow-intensive after confirming the target is a test system."
        )


def extract_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    """Read k6 summary-export metrics across supported summary value shapes.

    k6 versions/export formats may put values directly on a metric or inside
    its ``values`` object. Some summaries omit zero-only counters such as
    dropped_iterations, and checks may expose passes/fails without ``value``.
    """
    metrics = summary.get("metrics", {})

    def values_for(name: str) -> dict[str, Any]:
        metric = metrics.get(name, {})
        if not isinstance(metric, dict):
            return {}
        nested = metric.get("values")
        return nested if isinstance(nested, dict) else metric

    def required_number(name: str, field: str) -> float:
        values = values_for(name)
        try:
            return float(values[field])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"k6 summary is missing metric '{name}.{field}'.") from exc

    p95 = required_number("http_req_duration", "p(95)")
    request_rate = required_number("http_reqs", "rate")
    error_rate = required_number("http_req_failed", "value") * 100.0

    checks_values = values_for("checks")
    if "value" in checks_values:
        checks_rate = float(checks_values["value"])
    elif "passes" in checks_values and "fails" in checks_values:
        total_checks = float(checks_values["passes"]) + float(checks_values["fails"])
        if total_checks <= 0:
            raise ValueError("k6 summary contains no completed checks.")
        checks_rate = float(checks_values["passes"]) / total_checks
    else:
        raise ValueError("k6 summary is missing checks.value or checks passes/fails.")

    dropped_values = values_for("dropped_iterations")
    # k6 may omit a counter when its value is zero; a present but malformed
    # counter is still treated as an error rather than silently ignored.
    if not dropped_values:
        dropped = 0
    else:
        try:
            dropped = int(dropped_values.get("count", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("k6 summary has an invalid dropped_iterations.count.") from exc

    request_values = values_for("http_reqs")
    request_count = request_values.get("count")
    try:
        request_count = int(request_count) if request_count is not None else None
    except (TypeError, ValueError) as exc:
        raise ValueError("k6 summary has an invalid http_reqs.count.") from exc

    return {
        "p95_ms": round(p95, 3),
        "http_request_rate_per_sec": round(request_rate, 3),
        "http_error_rate_percent": round(error_rate, 4),
        "checks_rate": round(checks_rate, 5),
        "dropped_iterations": dropped,
        "http_requests": request_count,
    }


def evaluate(metrics: dict[str, Any], phase_config: dict[str, Any], sla: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "p95": metrics["p95_ms"] <= float(sla["p95_ms"]),
        "request_rate": metrics["http_request_rate_per_sec"] >= float(phase_config["min_request_rate"]),
        "http_error_rate": metrics["http_error_rate_percent"] <= float(sla["max_error_rate_percent"]),
        "checks": metrics["checks_rate"] >= float(sla["min_checks_rate"]),
        "dropped_iterations": metrics["dropped_iterations"] <= int(sla["max_dropped_iterations"]),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "targets": {
            "p95_ms_max": float(sla["p95_ms"]),
            "http_request_rate_per_sec_min": float(phase_config["min_request_rate"]),
            "http_error_rate_percent_max": float(sla["max_error_rate_percent"]),
            "checks_rate_min": float(sla["min_checks_rate"]),
            "dropped_iterations_max": int(sla["max_dropped_iterations"]),
        },
    }


def run_phase(
    phase_name: str,
    phase_config: dict[str, Any],
    profile: dict[str, Any],
    session_id: str,
    base_url: str,
) -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = REPORTS_DIR / f"{session_id}-{phase_name}-k6-summary.json"
    result_path = REPORTS_DIR / f"{session_id}-{phase_name}-result.json"

    env = os.environ.copy()
    env.update({
        "PERF_BASE_URL": base_url,
        "PERF_RATE": str(phase_config["rate"]),
        "PERF_DURATION": str(phase_config["duration"]),
        "PERF_PREALLOCATED_VUS": str(phase_config["pre_allocated_vus"]),
        "PERF_MAX_VUS": str(phase_config["max_vus"]),
    })
    command = [
        "k6", "run", f"--summary-export={summary_path}", str(SCENARIO_FILE)
    ]

    print("\n" + "=" * 58)
    print(f" PHASE: {phase_name.upper()}")
    print("=" * 58)
    print(f"Target URL : {base_url}")
    print(f"Arrival rate: {phase_config['rate']} HTTP requests/sec")
    print(f"Duration   : {phase_config['duration']}")
    print(f"Summary    : {summary_path}")

    phase_result: dict[str, Any] = {
        "phase": phase_name,
        "engine": "k6",
        "configuration": phase_config,
        "summary_file": str(summary_path.relative_to(ROOT)),
        "started_at": datetime.now().astimezone().isoformat(),
    }

    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.stdout:
            print(completed.stdout)
        if completed.stderr:
            print(completed.stderr, file=sys.stderr)
        phase_result["k6_exit_code"] = completed.returncode
        if completed.returncode != 0:
            raise RuntimeError(f"k6 exited with code {completed.returncode}.")
        if not summary_path.is_file():
            raise RuntimeError("k6 did not create the summary JSON file.")

        with summary_path.open("r", encoding="utf-8") as stream:
            raw_summary = json.load(stream)
        metrics = extract_metrics(raw_summary)
        gate = evaluate(metrics, phase_config, profile["sla"])
        phase_result.update({
            "status": gate["status"],
            "metrics": metrics,
            "gate": gate,
        })
        print("\nMeasured metrics")
        print(f"  P95 response time : {metrics['p95_ms']} ms")
        print(f"  HTTP request rate : {metrics['http_request_rate_per_sec']} req/sec")
        print(f"  HTTP error rate   : {metrics['http_error_rate_percent']}%")
        print(f"  Checks success    : {metrics['checks_rate'] * 100:.2f}%")
        print(f"  Dropped iterations: {metrics['dropped_iterations']}")
        print("\nPhase Gate")
        for key, value in gate["checks"].items():
            print(f"  {key.replace('_', ' ').title():22} {'PASS' if value else 'FAIL'}")
        print(f"\nPHASE RESULT: {gate['status']}")
    except Exception as exc:
        phase_result.update({
            "status": "ERROR",
            "error": str(exc),
        })
        print(f"\nPHASE EXECUTION ERROR: {exc}")
    finally:
        phase_result["finished_at"] = datetime.now().astimezone().isoformat()
        result_path.write_text(json.dumps(phase_result, indent=2), encoding="utf-8")
        phase_result["result_file"] = str(result_path.relative_to(ROOT))
    return phase_result


def write_final_report(session_id: str, profile: dict[str, Any], phases: list[dict[str, Any]]) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / f"{session_id}-pipeline-report.json"
    md_path = REPORTS_DIR / f"{session_id}-pipeline-report.md"
    overall = "PASS" if phases and all(p["status"] == "PASS" for p in phases) else "FAIL"
    payload = {
        "session_id": session_id,
        "application": profile["application"],
        "release": profile["release"],
        "overall_status": overall,
        "phases": phases,
        "generated_at": datetime.now().astimezone().isoformat(),
        "interpretation_note": (
            "The k6 rate is HTTP requests per second, not business transactions per second. "
            "Business TPS requires explicit transaction boundaries and transaction-level metrics."
        ),
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        f"# AI Performance Pipeline Report — {session_id}",
        "",
        f"- Application: {profile['application']}",
        f"- Release: {profile['release']}",
        f"- Overall result: **{overall}**",
        f"- Generated: {payload['generated_at']}",
        "",
        "> k6 reports HTTP requests per second. This is not automatically equivalent to business TPS.",
        "",
        "## Phase results",
        "",
        "| Phase | Status | P95 (ms) | HTTP req/sec | HTTP errors (%) | Checks success | Dropped iterations |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for phase in phases:
        m = phase.get("metrics", {})
        lines.append(
            f"| {phase['phase']} | {phase['status']} | "
            f"{m.get('p95_ms', 'N/A')} | {m.get('http_request_rate_per_sec', 'N/A')} | "
            f"{m.get('http_error_rate_percent', 'N/A')} | "
            f"{(m.get('checks_rate', 0) * 100):.2f}% | {m.get('dropped_iterations', 'N/A')} |"
        )
    lines.extend(["", "## Gate details", ""])
    for phase in phases:
        lines.append(f"### {phase['phase'].title()}: {phase['status']}")
        if phase.get("gate"):
            for key, passed in phase["gate"]["checks"].items():
                lines.append(f"- {key.replace('_', ' ').title()}: {'PASS' if passed else 'FAIL'}")
        elif phase.get("error"):
            lines.append(f"- Execution error: {phase['error']}")
        lines.append("")
    if overall != "PASS":
        lines.extend([
            "## Next action",
            "",
            "The pipeline stopped at the first failed or errored phase. Review its raw k6 summary,",
            "application logs and infrastructure/APM telemetry before claiming a root cause.",
            "Remediation and retesting require review; this pipeline does not modify the application.",
            "",
        ])
    else:
        lines.extend([
            "## Next action",
            "",
            "All selected phases passed their configured gates. This result applies only to the",
            "selected target, workload, test window and available telemetry.",
            "",
        ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run selected k6 phases with sequential Phase Gates and consolidated reporting."
    )
    parser.add_argument(
        "--phases",
        default="baseline",
        help="Comma-separated ordered phases: baseline,load,stress,spike,soak (default: baseline)",
    )
    parser.add_argument("--allow-intensive", action="store_true",
                        help="Explicitly permit load/stress/spike/soak traffic.")
    parser.add_argument("--base-url", default=None,
                        help="Override target URL; default comes from config/performance_profile.json.")
    args = parser.parse_args()

    try:
        profile = load_profile()
        phases = [p.strip().lower() for p in args.phases.split(",") if p.strip()]
        validate_phases(phases, profile, args.allow_intensive)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    base_url = args.base_url or os.environ.get("PERF_BASE_URL") or profile["base_url"]
    session_id = "PERF-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    print("=" * 58)
    print(" AI PERFORMANCE ENGINEERING PIPELINE")
    print("=" * 58)
    print(f"Session    : {session_id}")
    print(f"Application: {profile['application']}")
    print(f"Release    : {profile['release']}")
    print(f"Phases     : {' -> '.join(phases)}")
    print(f"Target URL : {base_url}")

    results: list[dict[str, Any]] = []
    for phase_name in phases:
        result = run_phase(
            phase_name, profile["phases"][phase_name], profile, session_id, base_url
        )
        results.append(result)
        if result["status"] != "PASS":
            print(f"\nSTOP: phase '{phase_name}' returned {result['status']}; later phases were not started.")
            break
        print(f"Phase '{phase_name}' passed.")
        if phase_name != phases[-1]:
            print(f"Proceeding to selected next phase: {phases[phases.index(phase_name) + 1]}")

    json_report, md_report = write_final_report(session_id, profile, results)
    overall = "PASS" if results and all(p["status"] == "PASS" for p in results) and len(results) == len(phases) else "FAIL"
    print("\n" + "=" * 58)
    print(f"PIPELINE RESULT: {overall}")
    print(f"JSON report : {json_report}")
    print(f"Markdown    : {md_report}")
    print("=" * 58)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
