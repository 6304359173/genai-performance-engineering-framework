import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
METRICS_FILE = BASE_DIR / "python-engine" / "metrics.json"


def classify_failure(metrics):

    performance = metrics["performance_metrics"]
    sla = metrics["sla"]

    p95 = performance["p95_ms"]
    tps = performance["tps"]
    error_rate = performance["error_rate_percent"]

    target_p95 = sla["required_p95_ms"]
    target_tps = sla["required_tps"]
    target_error = sla["required_error_rate_percent"]

    # 1. Throughput failure
    if tps < target_tps:

        return {
            "category": "THROUGHPUT",
            "reason": f"TPS {tps} is below target {target_tps}",
            "confidence": "HIGH"
        }

    # 2. Response time failure
    if p95 > target_p95:

        return {
            "category": "RESPONSE_TIME",
            "reason": f"P95 {p95} ms exceeds target {target_p95} ms",
            "confidence": "HIGH"
        }

    # 3. Error-rate failure
    if error_rate > target_error:

        return {
            "category": "ERROR_RATE",
            "reason": f"Error rate {error_rate}% exceeds target {target_error}%",
            "confidence": "HIGH"
        }

    # 4. Check detailed failure analysis
    failure_analysis = metrics.get("failure_analysis", {})
    response_codes = failure_analysis.get("by_response_code", {})

    for code, data in response_codes.items():

        if str(code).startswith("5"):

            return {
                "category": "SERVER_ERROR",
                "reason": f"HTTP {code} responses detected",
                "confidence": "HIGH"
            }

    return {
        "category": "UNKNOWN",
        "reason": "SLA failure detected but root cause could not be classified",
        "confidence": "LOW"
    }


def main():

    print()
    print("===================================")
    print("       FAILURE CLASSIFICATION")
    print("===================================")

    with open(METRICS_FILE, "r") as f:
        metrics = json.load(f)

    result = classify_failure(metrics)

    print(f"Category   : {result['category']}")
    print(f"Reason     : {result['reason']}")
    print(f"Confidence : {result['confidence']}")


if __name__ == "__main__":
    main()