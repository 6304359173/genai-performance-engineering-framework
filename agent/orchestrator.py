
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

from phase_gate import PhaseGate


class PerformanceAgent:

    def __init__(self):
        self.session_id = (
            "PERF-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        )

    def analyze_requirement(self, requirement):

        print("\n==================================================")
        print(" AI PERFORMANCE ENGINEERING AGENT")
        print("==================================================")

        print(f"\nSession ID : {self.session_id}")
        print(f"Application: {requirement['application']}")
        print(f"Release    : {requirement['release']}")
        print(f"Objective  : {requirement['test_type']}")

        print("\nAnalyzing performance requirements...")

        workload = {
            "users": requirement["users"],
            "target_tps": requirement["target_tps"],
            "p95_ms": requirement["p95_ms"],
            "error_rate_percent": requirement["error_rate_percent"]
        }

        print("✓ Requirements identified")

        print("\nWorkload Model")
        print("--------------------------------")
        print(f"Users          : {workload['users']}")
        print(f"Target TPS     : {workload['target_tps']}")
        print(f"P95 Target     : <= {workload['p95_ms']} ms")
        print(
            f"Error Rate     : <= "
            f"{workload['error_rate_percent']}%"
        )

        return workload

    def select_engine(self, test_type):

        print("\nSelecting performance engine...")

        if test_type.lower() == "baseline":
            engine = "k6"
            reason = (
                "Baseline validation is lightweight and suitable for k6."
            )
        else:
            engine = "JMeter"
            reason = (
                "Enterprise load testing with complex workload modeling "
                "is currently assigned to JMeter."
            )

        print(f"✓ Engine selected : {engine}")
        print(f"  Reason          : {reason}")

        return {
            "engine": engine,
            "reason": reason
        }

    def create_test_plan(self, requirement, workload, engine):

        print("\nCreating performance test plan...")

        plan = {
            "session_id": self.session_id,
            "application": requirement["application"],
            "release": requirement["release"],
            "test_type": requirement["test_type"],
            "engine": engine["engine"],
            "workload": workload,
            "created_at": datetime.now().isoformat()
        }

        print("✓ Test plan created")

        return plan

    def execute_phase(self, plan):

        print("\n==================================================")
        print(" PHASE EXECUTION")
        print("==================================================")

        print(f"\nPhase  : {plan['test_type'].upper()}")
        print(f"Engine : {plan['engine']}")

        if plan["engine"].lower() != "k6":
            raise NotImplementedError(
                "Real execution is currently implemented for k6 only. "
                "JMeter integration is still pending."
            )

        project_root = Path(__file__).resolve().parent.parent
        script_path = project_root / "tests" / "baseline.js"
        reports_dir = project_root / "reports"

        reports_dir.mkdir(parents=True, exist_ok=True)

        summary_path = (
            reports_dir / f"{plan['session_id']}-summary.json"
        )

        if not script_path.is_file():
            raise FileNotFoundError(
                f"k6 test script not found: {script_path}"
            )

        print(f"\nTest script : {script_path}")
        print(f"Summary file: {summary_path}")

        command = [
            "k6",
            "run",
            f"--summary-export={summary_path}",
            str(script_path)
        ]

        print("\nExecuting real k6 test...")

        try:
            completed = subprocess.run(
                command,
                cwd=str(project_root),
                capture_output=True,
                text=True
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Could not launch k6. Verify that k6 is installed "
                "and available in PATH."
            ) from exc

        if completed.stdout:
            print("\n--- k6 output ---")
            print(completed.stdout)

        if completed.stderr:
            print("\n--- k6 diagnostics ---")

            print(completed.stderr)

        if not summary_path.is_file():
            raise RuntimeError(
                "k6 did not create its summary file. "
                f"Exit code: {completed.returncode}"

            )
        if completed.returncode != 0:
            raise RuntimeError(
                f"k6 execution failed with exit code "
                f"{completed.returncode}. "
                "Review the k6 output above before trusting the metrics."
            )

        try:
            with summary_path.open("r", encoding="utf-8") as file:
                summary = json.load(file)

            metric_data = summary["metrics"]

            p95_ms = metric_data["http_req_duration"]["p(95)"]
            request_rate = metric_data["http_reqs"]["rate"]
            failed_rate = metric_data["http_req_failed"]["value"]

            metrics = {
                "p95_ms": round(float(p95_ms), 3),
                "tps": round(float(request_rate), 3),
                "error_rate_percent": round(
                    float(failed_rate) * 100, 4
                )
            }

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(
                f"Could not extract required metrics from {summary_path}"
            ) from exc

        print("\n✓ Real performance metrics extracted")
        print(f"P95 response time : {metrics['p95_ms']} ms")
        print(
            f"HTTP request rate : {metrics['tps']} requests/sec"
        )
        print(f"HTTP failure rate  : {metrics['error_rate_percent']}%")
        print(f"k6 exit code       : {completed.returncode}")

        return metrics

    def evaluate_phase(self, plan, metrics):

        print("\n==================================================")
        print(" PHASE GATE")
        print("==================================================")

        sla = {
            "p95_ms": plan["workload"]["p95_ms"],
            "tps": plan["workload"]["target_tps"],
            "error_rate_percent": (
                plan["workload"]["error_rate_percent"]
            )
        }

        gate = PhaseGate(sla)
        result = gate.evaluate(metrics)

        print(f"\nP95         : {metrics['p95_ms']} ms")
        print(f"Target P95  : <= {sla['p95_ms']} ms")

        print(f"\nHTTP req/sec: {metrics['tps']}")
        print(f"Target rate : >= {sla['tps']} req/sec")

        print(f"\nError Rate  : {metrics['error_rate_percent']}%")
        print(f"Target      : <= {sla['error_rate_percent']}%")

        print("\nChecks:")

        print(
            f"  P95         : "
            f"{'PASS' if result['checks']['p95'] else 'FAIL'}"
        )
        print(
            f"  Request rate: "
            f"{'PASS' if result['checks']['tps'] else 'FAIL'}"
        )
        print(
            f"  Error Rate  : "
            f"{'PASS' if result['checks']['error_rate'] else 'FAIL'}"
        )

        print("\n--------------------------------------")
        print(f"PHASE RESULT : {result['status']}")
        print("--------------------------------------")

        return result

    def generate_rca(self, plan, metrics, gate_result):

        print("\n==================================================")
        print(" AI ROOT CAUSE ANALYSIS")
        print("==================================================")

        project_root = Path(__file__).resolve().parent.parent
        ai_engine_dir = project_root / "ai-engine"
        reports_dir = project_root / "reports"

        reports_dir.mkdir(parents=True, exist_ok=True)

        report_path = (
            reports_dir / f"{plan['session_id']}-rca.md"
        )

        try:
            if str(ai_engine_dir) not in sys.path:
                sys.path.insert(0, str(ai_engine_dir))

            from llm_client import (
                is_llm_configured,
                generate_ai_rca
            )

            if not is_llm_configured():
                print("RCA skipped: Ollama/Qwen3:8b is not available.")
                print("Check that Ollama is running and the model is installed.")
                return

            evidence = {
                "session_id": plan["session_id"],
                "application": plan["application"],
                "release": plan["release"],
                "test_type": plan["test_type"],
                "engine": plan["engine"],
                "workload": plan["workload"],
                "measured_metrics": {
                    "p95_response_time_ms": metrics["p95_ms"],
                    "http_request_rate_per_second": metrics["tps"],
                    "http_failure_rate_percent": (
                        metrics["error_rate_percent"]
                    )
                },
                "phase_gate_result": gate_result,
                "evidence_limitations": [
                    "The measured rate is HTTP requests per second. "
                    "It is not independently verified business TPS.",
                    "No server CPU, memory, garbage collection, database, "
                    "network, or APM telemetry was supplied.",
                    "Do not claim a definitive root cause without "
                    "supporting evidence."
                ]
            }

            prompt = f"""
You are a Senior Performance Engineer and Performance Architect.

Analyze this performance test using only the supplied evidence.

Provide these sections:
1. Executive Summary
2. Measured Facts
3. SLA and Phase Gate Assessment
4. Potential Causes (clearly label as hypotheses)
5. Additional Telemetry Required
6. Prioritized Recommendations
7. Controlled Retest Strategy
8. Final Engineering Conclusion

Important rules:
- Separate confirmed facts from hypotheses.
- Do not invent metrics, logs, or infrastructure details.
- Do not confuse HTTP request rate with business TPS.
- The Phase Gate result is authoritative for PASS or FAIL.
- Do not claim a bottleneck is confirmed without evidence.
- Remediation and retesting have not yet been performed.
- Recommend actions; do not claim they were executed.

Performance evidence:
{json.dumps(evidence, indent=2)}
"""

            print("Checking local Ollama model...")
            print("Sending performance evidence to Qwen3:8b...")

            rca_report = generate_ai_rca(prompt)

            if not isinstance(rca_report, str) or not rca_report.strip():
                raise RuntimeError("The LLM returned an empty RCA report.")

            report_content = (
                "# AI Performance RCA Report\n\n"
                f"- Session: {plan['session_id']}\n"
                f"- Application: {plan['application']}\n"
                f"- Release: {plan['release']}\n"
                f"- Test type: {plan['test_type']}\n"
                f"- Phase Gate: {gate_result['status']}\n\n"
                "---\n\n"
                f"{rca_report.strip()}\n"
            )

            report_path.write_text(
                report_content,
                encoding="utf-8"
            )

            print("\n✓ RCA report generated successfully")
            print(f"Report location: {report_path}")

        except Exception as exc:
            print("\n✗ RCA generation failed.")
            print(f"Reason: {exc}")
            print("The original Phase Gate result remains unchanged.")

    def run(self, requirement):

        workload = self.analyze_requirement(requirement)

        engine = self.select_engine(requirement["test_type"])

        plan = self.create_test_plan(
            requirement,
            workload,
            engine
        )

        print("\n==================================================")
        print(" TEST PLAN READY")
        print("==================================================")
        print(json.dumps(plan, indent=2))

        metrics = self.execute_phase(plan)

        gate_result = self.evaluate_phase(plan, metrics)

        print("\n==================================================")
        print(" AGENT DECISION")
        print("==================================================")

        if gate_result["status"] == "PASS":
            print("✓ Phase PASSED")
            print("→ Proceed to next phase")
        else:
            print("✗ Phase FAILED")
            print("→ Stop progression")
            print("→ Trigger AI RCA")

        # Generate an evidence-based report for either outcome.
        self.generate_rca(plan, metrics, gate_result)

        print("→ Review RCA recommendations")
        print("→ Remediation and retest require approval")


if __name__ == "__main__":

    requirement = {
        "application": "AI Order Service",
        "release": "5.2",
        "test_type": "baseline",
        "users": 1,
        "target_tps": 10,
        "p95_ms": 2000,
        "error_rate_percent": 1
    }

    agent = PerformanceAgent()
    agent.run(requirement)
