import json
import os


# ============================================================
# AI RCA Client
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

METRICS_FILE = os.path.join(
    BASE_DIR,
    "python-engine",
    "metrics.json"
)

PROMPT_FILE = os.path.join(
    BASE_DIR,
    "ai-engine",
    "rca_prompt.txt"
)


def load_metrics():
    """
    Load the latest performance evidence.
    """

    if not os.path.exists(METRICS_FILE):
        raise FileNotFoundError(
            f"Metrics file not found: {METRICS_FILE}"
        )

    with open(
        METRICS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def build_rca_prompt(metrics):
    """
    Build an AI RCA prompt from deterministic
    performance evidence.
    """

    prompt = f"""
You are a Senior Performance Engineer.

Analyze the following performance test evidence.

PERFORMANCE EVIDENCE
====================

Test Summary:
{json.dumps(metrics.get("test_summary", {}), indent=2)}

Performance Metrics:
{json.dumps(metrics.get("performance_metrics", {}), indent=2)}

SLA Results:
{json.dumps(metrics.get("sla", {}), indent=2)}


RCA INSTRUCTIONS
================

1. Identify which SLA requirements passed and failed.
2. Explain the observed performance behavior.
3. Do NOT invent infrastructure or application metrics.
4. Do NOT declare a root cause without supporting evidence.
5. Identify possible causes as hypotheses only.
6. Identify what additional telemetry is required.
7. Recommend the next performance investigation steps.
8. Clearly separate:
   - Facts
   - Hypotheses
   - Required evidence
   - Recommended actions

Return the analysis in a structured format.
"""

    return prompt


def save_prompt(prompt):

    os.makedirs(
        os.path.dirname(PROMPT_FILE),
        exist_ok=True
    )

    with open(
        PROMPT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(prompt)


if __name__ == "__main__":

    print("====================================")
    print(" AI Performance RCA Client")
    print("====================================")

    metrics = load_metrics()

    prompt = build_rca_prompt(metrics)

    save_prompt(prompt)

    print()
    print("RCA prompt generated successfully.")
    print()
    print(f"Input : {METRICS_FILE}")
    print(f"Output: {PROMPT_FILE}")