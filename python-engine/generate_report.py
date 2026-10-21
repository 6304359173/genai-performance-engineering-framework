import json
import os
from datetime import datetime

BASE_DIR = os.environ.get(
    "WORKSPACE",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

METRICS_FILE = os.path.join(
    BASE_DIR, "python-engine", "metrics.json"
)

REPORT_DIR = os.path.join(
    BASE_DIR, "reports"
)

REPORT_FILE = os.path.join(
    REPORT_DIR, "ai_rca_report.md"
)

# Create reports directory if it does not exist
os.makedirs(REPORT_DIR, exist_ok=True)

# Load metrics
with open(METRICS_FILE, "r", encoding="utf-8") as file:
    metrics = json.load(file)

# Read nested sections
summary = metrics["test_summary"]
performance = metrics["performance_metrics"]
sla = metrics["sla"]

# Test summary
total = summary["total_requests"]
success = summary["successful_requests"]
failed = summary["failed_requests"]
duration = summary["test_duration_seconds"]

# Performance metrics
avg = performance["average_response_time_ms"]
minimum = performance["min_response_time_ms"]
maximum = performance["max_response_time_ms"]
p90 = performance["p90_ms"]
p95 = performance["p95_ms"]
p99 = performance["p99_ms"]
tps = performance["tps"]
error_rate = performance["error_rate_percent"]

# SLA
required_p95 = sla["required_p95_ms"]
required_tps = sla["required_tps"]
required_error_rate = sla["required_error_rate_percent"]

p95_status = sla["p95_status"]
tps_status = sla["tps_status"]
error_status = sla["error_rate_status"]
overall_status = sla["overall_status"]

# Generate report
report = f"""# AI Performance RCA Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 1. Executive Summary

The performance test executed **{total} requests** over
approximately **{duration} seconds**.

- Successful Requests: {success}
- Failed Requests: {failed}
- Average Response Time: {avg:.2f} ms
- P95 Response Time: {p95:.2f} ms
- P99 Response Time: {p99:.2f} ms
- Throughput: {tps:.2f} TPS
- Error Rate: {error_rate:.2f}%

Overall SLA Status: **{overall_status}**

---

## 2. SLA Assessment

| Metric | Actual | SLA | Status |
|---|---:|---:|---|
| P95 Response Time | {p95:.2f} ms | <= {required_p95} ms | {p95_status} |
| TPS | {tps:.2f} | >= {required_tps} | {tps_status} |
| Error Rate | {error_rate:.2f}% | <= {required_error_rate}% | {error_status} |

### SLA Interpretation

- **P95:** {p95_status}
- **Throughput:** {tps_status}
- **Error Rate:** {error_status}

---

## 3. Observed Facts

1. Total requests executed: **{total}**
2. Successful requests: **{success}**
3. Failed requests: **{failed}**
4. Average response time: **{avg:.2f} ms**
5. Minimum response time: **{minimum:.2f} ms**
6. Maximum response time: **{maximum:.2f} ms**
7. P90 response time: **{p90:.2f} ms**
8. P95 response time: **{p95:.2f} ms**
9. P99 response time: **{p99:.2f} ms**
10. Throughput: **{tps:.2f} TPS**
11. Error rate: **{error_rate:.2f}%**

---

## 4. Possible RCA Hypotheses

### Throughput

The measured throughput is **{tps:.2f} TPS**, while the target
is **{required_tps} TPS**.

However, this result alone does **not prove an application
capacity bottleneck**.

The test executed only {total} requests over {duration} seconds.

Possible areas to investigate:

- Application CPU
- Application memory
- JVM heap and garbage collection
- Application thread pools
- Database CPU
- Database query latency
- Database connection pool
- Network latency
- Kubernetes pod resources
- Load generator capacity
- Number of concurrent users

### Response Time

The P95 response time is **{p95:.2f} ms**, compared with the SLA
of **{required_p95} ms**.

Therefore the P95 response-time objective is currently **met**.

There is no evidence from the JMeter results alone that response
time is the primary bottleneck.

---

## 5. Evidence Required to Confirm RCA

To identify the actual root cause, collect:

### Application

- CPU utilization
- Memory utilization
- JVM heap
- GC activity
- Thread count
- Thread-pool utilization
- Connection-pool utilization

### Database

- Database CPU
- Query execution time
- Slow queries
- Lock waits
- Connection utilization

### Infrastructure

- Server CPU
- Memory
- Disk I/O
- Network latency
- Kubernetes pod CPU
- Kubernetes pod memory
- HPA activity

### APM

Use tools such as:

- Dynatrace PurePath
- AppDynamics transaction snapshots
- Datadog APM traces

The goal is to correlate the slow transaction with the
underlying resource or dependency.

---

## 6. Recommended Investigation

1. Establish a baseline.
2. Gradually increase concurrent users.
3. Monitor TPS and response-time percentiles.
4. Verify load-generator utilization.
5. Monitor application resources.
6. Monitor database resources.
7. Analyze APM traces.
8. Identify the first resource that reaches saturation.
9. Correlate that resource with the affected transaction.
10. Confirm the hypothesis using additional evidence.

---

## 7. Recommended Remediation

No production remediation should be recommended based only on
this small validation test.

Once sufficient evidence identifies the bottleneck, possible
remediation may include:

- Application optimization
- Database query optimization
- Connection-pool tuning
- Thread-pool tuning
- JVM tuning
- Horizontal scaling
- Kubernetes resource adjustment
- HPA tuning
- Caching
- Network optimization

The remediation should be selected based on measured evidence.

---

## 8. Performance Retest Strategy

After remediation:

### Step 1
Run the same baseline workload.

### Step 2
Run the target workload.

### Step 3
Compare:

- Average response time
- P90
- P95
- P99
- TPS
- Error rate

### Step 4
Compare infrastructure metrics before and after remediation.

### Step 5
Confirm that the improvement is repeatable.

### Step 6
Validate that no new bottleneck was introduced.

---

## 9. Final Engineering Conclusion

The current test achieved the configured response-time and
error-rate objectives.

The configured throughput target was not achieved.

However, because this was a very small validation workload,
the throughput result should **not automatically be interpreted
as proof of an application bottleneck**.

A larger controlled workload combined with application,
database, infrastructure and APM telemetry is required before
declaring a root cause.

---

## AI Performance Engineering Principle

> Do not declare a bottleneck from a single metric.

Correlate:

**Requirement → Workload → Response Time → TPS → Errors →
Infrastructure → Application → Database → APM Trace → Root Cause
→ Remediation → Retest → Validation**
"""

# Save report
with open(REPORT_FILE, "w", encoding="utf-8") as file:
    file.write(report)

print("====================================")
print(" AI Performance RCA Report")
print("====================================")
print()
print("Report generated successfully.")
print()
print(f"Report: {REPORT_FILE}")