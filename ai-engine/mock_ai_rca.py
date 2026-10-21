import json
import os


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

EVIDENCE_FILE = os.path.join(
    BASE_DIR,
    "ai-engine",
    "mcp_rca_evidence.json"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "ai-engine",
    "ai_rca_report.md"
)


def load_evidence():

    with open(
        EVIDENCE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def status_text(status):

    if status == "PASS":
        return "PASS"

    if status == "FAIL":
        return "FAIL"

    return status


def generate_rca(evidence):

    data = evidence["evidence"]

    summary = data["test_summary"]
    metrics = data["performance_metrics"]
    transaction_summary = data.get("transaction_summary", {})
    failure_analysis = data.get("failure_analysis", {})
    sla = data["sla"]

    p95_status = status_text(sla["p95_status"])
    tps_status = status_text(sla["tps_status"])
    error_status = status_text(sla["error_rate_status"])
    overall_status = status_text(sla["overall_status"])

    total_requests = summary["total_requests"]
    successful_requests = summary["successful_requests"]
    failed_requests = summary["failed_requests"]

    p95_ms = metrics["p95_ms"]
    tps = metrics["tps"]
    error_rate = metrics["error_rate_percent"]

    # ============================================================
    # Dynamic SLA Summary
    # ============================================================

    sla_results = []

    if p95_status == "PASS":
        sla_results.append(
            f"P95 response time passed ({p95_ms} ms)."
        )
    else:
        sla_results.append(
            f"P95 response time failed ({p95_ms} ms)."
        )

    if tps_status == "PASS":
        sla_results.append(
            f"Throughput passed ({tps} TPS)."
        )
    else:
        sla_results.append(
            f"Throughput failed ({tps} TPS)."
        )

    if error_status == "PASS":
        sla_results.append(
            f"Error rate passed ({error_rate}%)."
        )
    else:
        sla_results.append(
            f"Error rate failed ({error_rate}%)."
        )

    sla_summary = " ".join(sla_results)

    # ============================================================
    # Transaction Analysis
    # ============================================================

    transaction_lines = []

    for transaction, stats in transaction_summary.items():

        transaction_lines.append(
            f"| {transaction} | "
            f"{stats['total']} | "
            f"{stats['successful']} | "
            f"{stats['failed']} | "
            f"{stats['average_response_time_ms']} ms | "
            f"{stats['p95_ms']} ms | "
            f"{stats['p99_ms']} ms | "
            f"{stats['error_rate_percent']}% |"
        )

    if transaction_lines:

        transaction_table = "\n".join(transaction_lines)

    else:

        transaction_table = (
            "| No transaction-level data available | - | - | - | - | - | - | - |"
        )

    # ============================================================
    # Identify Slowest Transaction
    # ============================================================

    slowest_transaction = None

    if transaction_summary:

        slowest_transaction = max(
            transaction_summary.items(),
            key=lambda item: item[1]["p95_ms"]
        )

    # ============================================================
    # Failure Analysis
    # ============================================================

    sampler_failures = []

    for transaction, stats in failure_analysis.get(
        "by_sampler",
        {}
    ).items():

        if stats.get("failed", 0) > 0:

            sampler_failures.append(
                f"- **{transaction}**: "
                f"{stats['failed']} failed requests "
                f"({stats['error_rate_percent']}% error rate)"
            )

    response_code_failures = []

    for response_code, stats in failure_analysis.get(
        "by_response_code",
        {}
    ).items():

        if stats.get("failed", 0) > 0:

            response_code_failures.append(
                f"- HTTP {response_code}: "
                f"{stats['failed']} failed requests "
                f"out of {stats['total']}"
            )

    # ============================================================
    # RCA Assessment
    # ============================================================

    investigation_areas = []

    if error_status == "FAIL":

        investigation_areas.extend([
            "HTTP response codes and failed transactions.",
            "Application logs corresponding to failed requests.",
            "Application CPU, memory and event-loop/thread utilization.",
            "Application connection pools and concurrency limits.",
            "Database errors, connection limits and slow queries.",
            "APM traces for failed transactions."
        ])

    if p95_status == "FAIL":

        investigation_areas.extend([
            "Application response-time distribution.",
            "Backend service latency.",
            "Database query latency.",
            "External dependency latency."
        ])

    if tps_status == "FAIL":

        investigation_areas.extend([
            "Load-generator capacity.",
            "Application throughput limitations.",
            "Connection-pool saturation.",
            "Infrastructure resource limits."
        ])

    if overall_status == "PASS":

        rca_assessment = (
            "No SLA violation was observed. "
            "The available JMeter evidence does not establish a confirmed "
            "application, database, infrastructure or external dependency bottleneck."
        )

        if slowest_transaction:

            transaction_name = slowest_transaction[0]
            transaction_stats = slowest_transaction[1]

            rca_assessment += (
                f" Among the measured transactions, "
                f"**{transaction_name}** had the highest P95 response time "
                f"({transaction_stats['p95_ms']} ms). "
                f"This is an observation for further investigation, "
                f"not a confirmed root cause."
            )

    else:

        rca_assessment = (
            "One or more SLA criteria failed. "
            "The available performance evidence identifies the affected "
            "SLA dimensions, but it does not by itself prove the underlying "
            "root cause. Additional telemetry and correlation are required."
        )

    if not investigation_areas:

        investigation_areas.append(
            "No immediate SLA-driven investigation area was identified. "
            "Continue monitoring application, infrastructure and APM telemetry."
        )

    investigation_text = "\n".join(
        f"{index}. {item}"
        for index, item in enumerate(
            investigation_areas,
            1
        )
    )

    # ============================================================
    # Failure Section
    # ============================================================

    if sampler_failures:

        sampler_failure_text = "\n".join(
            sampler_failures
        )

    else:

        sampler_failure_text = (
            "No failed transactions were identified."
        )

    if response_code_failures:

        response_code_failure_text = "\n".join(
            response_code_failures
        )

    else:

        response_code_failure_text = (
            "No failed HTTP response codes were identified."
        )

    # ============================================================
    # Dynamic Engineering Conclusion
    # ============================================================

    if overall_status == "PASS":

        conclusion = (
            "All configured performance SLAs passed. "
            "No SLA violation was identified in this test. "
            "The transaction-level evidence also shows zero failed requests. "
            "No confirmed bottleneck can be established from JMeter evidence alone."
        )

    else:

        conclusion = (
            "The performance test failed one or more configured SLAs. "
            "The available evidence identifies the affected SLA criteria "
            "and transaction-level observations, but additional application, "
            "infrastructure, database and APM telemetry is required to "
            "confirm the root cause."
        )

    # ============================================================
    # Final Report
    # ============================================================

    report = f"""# AI Performance RCA Report

## 1. Executive Summary

The performance test executed **{total_requests} requests**.

Successful requests: **{successful_requests}**

Failed requests: **{failed_requests}**

Overall SLA status: **{overall_status}**

{sla_summary}

---

## 2. Performance Metrics

| Metric | Result |
|---|---:|
| Total Requests | {total_requests} |
| Successful Requests | {successful_requests} |
| Failed Requests | {failed_requests} |
| Test Duration | {summary["test_duration_seconds"]} sec |
| Average Response Time | {metrics["average_response_time_ms"]} ms |
| P90 | {metrics["p90_ms"]} ms |
| P95 | {metrics["p95_ms"]} ms |
| P99 | {metrics["p99_ms"]} ms |
| Maximum Response Time | {metrics["max_response_time_ms"]} ms |
| TPS | {tps} |
| Error Rate | {error_rate}% |

---

## 3. SLA Analysis

### P95 Response Time

Required: **{sla["required_p95_ms"]} ms**

Actual: **{p95_ms} ms**

Status: **{p95_status}**

---

### Throughput

Required: **{sla["required_tps"]} TPS**

Actual: **{tps} TPS**

Status: **{tps_status}**

---

### Error Rate

Required maximum: **{sla["required_error_rate_percent"]}%**

Actual: **{error_rate}%**

Status: **{error_status}**

---

## 4. Transaction Performance Analysis

| Transaction | Total | Success | Failed | Average | P95 | P99 | Error % |
|---|---:|---:|---:|---:|---:|---:|---:|
{transaction_table}

"""

    if slowest_transaction:

        transaction_name = slowest_transaction[0]
        transaction_stats = slowest_transaction[1]

        report += f"""
### Slowest Transaction Observation

**Transaction:** {transaction_name}

**Average Response Time:** {transaction_stats["average_response_time_ms"]} ms

**P95:** {transaction_stats["p95_ms"]} ms

**P99:** {transaction_stats["p99_ms"]} ms

**Error Rate:** {transaction_stats["error_rate_percent"]}%

This identifies the transaction with the highest P95 response time in the available
transaction-level evidence. It is an observation, not a confirmed root cause.
"""

    report += f"""
---

## 5. Failure Analysis

### Failures by Transaction

{sampler_failure_text}

### Failures by HTTP Response Code

{response_code_failure_text}

---

## 6. Performance Facts

- Total requests: **{total_requests}**
- Successful requests: **{successful_requests}**
- Failed requests: **{failed_requests}**
- P95 response time: **{p95_ms} ms**
- Throughput: **{tps} TPS**
- Error rate: **{error_rate}%**
- Overall SLA status: **{overall_status}**

These are observed test results and should be treated as performance facts.

---

## 7. RCA Assessment

{rca_assessment}

The following areas require investigation when SLA violations or performance
anomalies are observed:

{investigation_text}

These are investigation areas and hypotheses only.
They should be validated using application, infrastructure, database and APM telemetry.

---

## 8. Required Evidence

### Application

- CPU utilization
- Memory utilization
- JVM/Node.js process metrics
- Thread or event-loop utilization
- Connection-pool usage
- Application logs
- HTTP response codes

### Database

- CPU utilization
- Active connections
- Query response time
- Slow queries
- Lock/wait statistics
- Database errors

### Infrastructure

- CPU
- Memory
- Network throughput
- Disk I/O
- Container/Kubernetes resource utilization

### APM

- Transaction response time
- Backend call duration
- Database call duration
- External service latency
- Distributed traces
- Failed transaction traces

---

## 9. Recommended Next Actions

1. Review transaction-level response-time distribution.
2. Review failed transactions when failures are present.
3. Group failures by sampler and response code.
4. Correlate performance anomalies with application logs.
5. Capture application and infrastructure metrics.
6. Capture APM transaction traces.
7. Capture database performance metrics.
8. Correlate errors and latency with backend dependencies.
9. Identify the confirmed bottleneck or failure cause.
10. Apply remediation.
11. Re-run the performance test.
12. Validate the SLA again.

---

## 10. Engineering Conclusion

{conclusion}

The next performance-engineering step is:

**Measure -> Correlate -> Identify Bottleneck -> Remediate -> Retest -> Validate**
"""

    return report


if __name__ == "__main__":

    print("====================================")
    print(" Mock AI Performance RCA")
    print("====================================")

    evidence = load_evidence()

    print()
    print("MCP evidence loaded.")
    print()

    report = generate_rca(evidence)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(report)

    print("Mock AI RCA generated successfully.")
    print()
    print(f"Output: {OUTPUT_FILE}")