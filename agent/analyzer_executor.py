import subprocess
from pathlib import Path
import json


class AnalyzerExecutor:

    def __init__(self):
        self.project_dir = Path(__file__).resolve().parent.parent

        self.analyzer = (
            self.project_dir
            / "python-engine"
            / "analyzer.py"
        )

        self.metrics_file = (
            self.project_dir
            / "python-engine"
            / "metrics.json"
        )

    def run(self):

        print("\n===================================")
        print("       PERFORMANCE ANALYSIS")
        print("===================================")

        if not self.analyzer.exists():
            raise FileNotFoundError(
                f"Analyzer not found: {self.analyzer}"
            )

        command = [
            "python",
            str(self.analyzer)
        ]

        result = subprocess.run(
            command,
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )

        print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:
            raise RuntimeError(
                f"Analyzer failed with exit code "
                f"{result.returncode}"
            )

        if not self.metrics_file.exists():
            raise RuntimeError(
                "Analyzer completed but metrics.json "
                "was not created."
            )

        with open(self.metrics_file, "r") as f:
            metrics = json.load(f)

        print("Metrics successfully loaded.")

        return metrics


if __name__ == "__main__":

    analyzer = AnalyzerExecutor()

    metrics = analyzer.run()

    print("\nMetrics:")
    print(json.dumps(metrics, indent=2))