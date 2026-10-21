import os
import json
import urllib.request
import urllib.error


# ============================================================
# Paths
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

AI_ENGINE_DIR = os.path.join(
    BASE_DIR,
    "ai-engine"
)

PROMPT_FILE = os.path.join(
    AI_ENGINE_DIR,
    "rca_prompt.txt"
)

OUTPUT_FILE = os.path.join(
    AI_ENGINE_DIR,
    "ai_rca_report.md"
)


# ============================================================
# Local Ollama Configuration
# ============================================================

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3:8b"


# ============================================================
# Check Local LLM
# ============================================================

def is_llm_configured():

    try:

        request = urllib.request.Request(
            "http://localhost:11434/api/tags",
            method="GET"
        )

        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        for model in data.get("models", []):

            if model.get("name") == OLLAMA_MODEL:

                return True

        return False

    except Exception:

        return False


# ============================================================
# Load RCA Prompt
# ============================================================

def load_rca_prompt():

    if not os.path.exists(PROMPT_FILE):

        raise FileNotFoundError(
            f"RCA prompt not found: {PROMPT_FILE}"
        )

    with open(
        PROMPT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return file.read()


# ============================================================
# Generate AI RCA using Local Qwen3
# ============================================================


def generate_ai_rca(prompt):

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (                   

    "You are a Senior Performance Engineer "
    "and Performance Architect. Analyze the "
    "provided performance evidence carefully. "

    "Separate confirmed FACTS from HYPOTHESES. "
    "Never invent missing metrics or evidence. "

    "CRITICAL SLA RULES: "
    "Use the supplied Phase Gate results as authoritative. "
    "Do not independently change a supplied PASS or FAIL verdict. "
    "If gate results are not supplied, calculate each SLA "
    "comparison correctly using the stated target and measured value. "
    "For a maximum latency SLA, actual latency less than or equal "
    "to the limit passes. For a minimum throughput SLA, actual "
    "throughput greater than or equal to the target passes. "
    "For a maximum error-rate SLA, actual error rate less than "
    "or equal to the limit passes. "

    "METRIC VALIDATION RULES: "
    "Check for contradictory or inconsistent metric fields. "
    "If fields conflict, explicitly flag the inconsistency and "
    "state that the affected metric needs verification. "
    "Do not claim a 100 percent failure rate solely from conflicting "
    "fields. Distinguish HTTP request rate from business TPS. "
    "Do not treat HTTP requests per second as verified business TPS. "

    "ROOT CAUSE RULES: "
    "Identify bottlenecks only when evidence supports them. "
    "Label unverified explanations as hypotheses. "
    "Do not claim that a hypothesis is a confirmed root cause. "
    "Identify additional logs, APM data, database metrics, "
    "and infrastructure telemetry needed for investigation. "

    "REPORT STRUCTURE: "
    "Include Executive Summary, Measured Facts, SLA and Phase "
    "Gate Assessment, Potential Causes, Additional Telemetry "
    "Required, Prioritized Recommendations, Controlled Retest "
    "Strategy, and Final Engineering Conclusion. "

    "Clearly state what is known, what remains uncertain, "
    "and what must be verified before retesting. "
    "Never claim remediation or retesting has been performed "
    "unless the supplied evidence confirms it."


                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 700
        }
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=900
        ) as response:

            response_data = json.loads(
                response.read().decode("utf-8")
            )

        if "error" in response_data:
            raise RuntimeError(response_data["error"])

        message = response_data.get("message", {})
        result = message.get("content", "")

        if not result.strip():
            raise RuntimeError(
                "Ollama returned an empty response."
            )

        return result

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Unable to connect to Ollama or receive its response: {error}"
        )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print("====================================")
    print(" AI Performance LLM Client")
    print("====================================")
    print()

    print(
        f"RCA Prompt: {PROMPT_FILE}"
    )
    print()

    print(
        f"Local LLM  : {OLLAMA_MODEL}"
    )

    print(
        f"Ollama URL : {OLLAMA_URL}"
    )
    print()

    # --------------------------------------------------------
    # Load RCA Prompt
    # --------------------------------------------------------

    try:

        prompt = load_rca_prompt()

    except Exception as error:

        print(
            f"ERROR: {error}"
        )

        raise SystemExit(1)

    print(
        "RCA prompt loaded successfully."
    )
    print()

    print(
        f"Prompt size: {len(prompt)} characters"
    )
    print()

    # --------------------------------------------------------
    # Check Local LLM
    # --------------------------------------------------------

    if not is_llm_configured():

        print(
            "LLM Status : NOT AVAILABLE"
        )
        print()

        print(
            f"{OLLAMA_MODEL} was not found in Ollama."
        )

        print(
            "Make sure Ollama is running."
        )

        raise SystemExit(1)

    print(
        "LLM Status : READY"
    )
    print()

    # --------------------------------------------------------
    # Send RCA Prompt to Qwen3
    # --------------------------------------------------------

    print(
        "Sending performance evidence to local Qwen3..."
    )
    print()

    try:

        result = generate_ai_rca(prompt)

        # ----------------------------------------------------
        # Save RCA report
        # ----------------------------------------------------

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(result)

        print(
            "AI RCA generated successfully."
        )
        print()

        print(
            f"Output: {OUTPUT_FILE}"
        )

        print()

        print(
            "===================================="
        )

        print(
            " AI RCA COMPLETE"
        )

        print(
            "===================================="
        )

    except Exception as error:

        print(
            "ERROR: LLM RCA generation failed."
        )

        print()

        print(
            f"Reason: {error}"
        )