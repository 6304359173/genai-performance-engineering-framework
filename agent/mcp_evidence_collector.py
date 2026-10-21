import json
import subprocess
from pathlib import Path


class MCPEvidenceCollector:

    def __init__(self):
        self.project_dir = Path(__file__).resolve().parent.parent

        self.mcp_client = (
            self.project_dir
            / "mcp-server"
            / "mcp_client.py"
        )

        self.evidence_file = (
            self.project_dir
            / "ai-engine"
            / "mcp_rca_evidence.json"
        )

    def collect(self):

        print("\n===================================")
        print("       MCP EVIDENCE COLLECTION")
        print("===================================")

        if not self.mcp_client.exists():
            raise FileNotFoundError(
                f"MCP client not found: {self.mcp_client}"
            )

        command = [
            "python",
            str(self.mcp_client)
        ]

        print("Calling existing MCP client...")
        print()

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
                f"MCP evidence collection failed. "
                f"Exit code: {result.returncode}"
            )

        if not self.evidence_file.exists():
            raise RuntimeError(
                "MCP completed but evidence file "
                "was not created."
            )

        with open(self.evidence_file, "r") as f:
            evidence = json.load(f)

        print("\nMCP evidence successfully collected.")

        print("\nEvidence sections:")

        if isinstance(evidence, dict):
            for key in evidence:
                print(f" - {key}")

        return evidence


if __name__ == "__main__":

    collector = MCPEvidenceCollector()

    evidence = collector.collect()

    print("\n===================================")
    print("       MCP EVIDENCE SUMMARY")
    print("===================================")

    print(json.dumps(evidence, indent=2))