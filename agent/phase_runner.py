from analyzer_executor import AnalyzerExecutor
from phase_gate import PhaseGate


class PhaseRunner:

    def __init__(self, sla):
        self.sla = sla
        self.analyzer = AnalyzerExecutor()
        self.gate = PhaseGate(sla)

    def run(self):

        print("\n===================================")
        print("          PHASE RUNNER")
        print("===================================")

        metrics = self.analyzer.run()

        performance = metrics["performance_metrics"]

        gate_metrics = {
            "p95_ms": performance["p95_ms"],
            "tps": performance["tps"],
            "error_rate_percent": performance["error_rate_percent"]
        }

        print("\n===================================")
        print("          PHASE GATE")
        print("===================================")

        result = self.gate.evaluate(gate_metrics)

        print(f"P95        : {gate_metrics['p95_ms']} ms")
        print(f"TPS        : {gate_metrics['tps']}")
        print(
            f"Error Rate : "
            f"{gate_metrics['error_rate_percent']}%"
        )

        print(f"\nPHASE RESULT: {result['status']}")

        if result["status"] == "PASS":

            print("\nAGENT DECISION")
            print("----------------")
            print("Phase PASSED")
            print("Proceed to next phase")

        else:

            print("\nAGENT DECISION")
            print("----------------")
            print("Phase FAILED")
            print("STOP progression")
            print("Trigger RCA")
            print("Collect evidence")
            print("Determine remediation")
            print("Retest after remediation")

        return result


if __name__ == "__main__":

    sla = {
        "p95_ms": 2000,
        "tps": 100,
        "error_rate_percent": 1
    }

    runner = PhaseRunner(sla)

    runner.run()