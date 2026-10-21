class PhaseGate:

    def __init__(self, sla):
        self.sla = sla

    def evaluate(self, metrics):

        p95 = metrics["p95_ms"]
        tps = metrics["tps"]
        error_rate = metrics["error_rate_percent"]

        checks = {
            "p95": p95 <= self.sla["p95_ms"],
            "tps": tps >= self.sla["tps"],
            "error_rate": error_rate <= self.sla["error_rate_percent"]
        }

        passed = all(checks.values())

        if passed:
            status = "PASS"
        else:
            status = "FAIL"

        return {
            "status": status,
            "checks": checks,
            "metrics": metrics,
            "sla": self.sla
        }


if __name__ == "__main__":

    sla = {
        "p95_ms": 2000,
        "tps": 10,
        "error_rate_percent": 1
    }

    # Temporary test result.
    # Later this will come from k6/JMeter.
    metrics = {
        "p95_ms": 3500,
        "tps": 12,
        "error_rate_percent": 0.2
    }

    gate = PhaseGate(sla)

    result = gate.evaluate(metrics)

    print("\n======================================")
    print(" PERFORMANCE PHASE GATE")
    print("======================================")

    print(f"\nP95         : {metrics['p95_ms']} ms")
    print(f"Target P95  : {sla['p95_ms']} ms")

    print(f"\nTPS         : {metrics['tps']}")
    print(f"Target TPS  : {sla['tps']}")

    print(f"\nError Rate  : {metrics['error_rate_percent']}%")
    print(f"Target      : {sla['error_rate_percent']}%")

    print("\nChecks:")
    print(f"  P95         : {'PASS' if result['checks']['p95'] else 'FAIL'}")
    print(f"  TPS         : {'PASS' if result['checks']['tps'] else 'FAIL'}")
    print(
        f"  Error Rate  : "
        f"{'PASS' if result['checks']['error_rate'] else 'FAIL'}"
    )

    print("\n--------------------------------------")
    print(f"PHASE RESULT : {result['status']}")
    print("--------------------------------------")

    if result["status"] == "PASS":
        print("\nNext Action:")
        print("  → Proceed to next performance phase")
    else:
        print("\nNext Action:")
        print("  → Stop progression")
        print("  → Trigger RCA")
        print("  → Remediation")
        print("  → Retest")