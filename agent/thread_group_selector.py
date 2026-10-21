import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
METRICS_FILE = BASE_DIR / "python-engine" / "metrics.json"


def load_metrics():

    with open(METRICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def select_thread_group():

    metrics = load_metrics()

    sla = metrics["sla"]

    target_tps = sla["required_tps"]
    target_p95 = sla["required_p95_ms"]

    # Current workload information
    current_users = 10
    current_ramp_up = 30
    current_duration = 60

    # Current test objective
    test_type = "LOAD"

    print()
    print("===================================")
    print("       THREAD GROUP SELECTOR")
    print("===================================")

    print()
    print("WORKLOAD REQUIREMENT")
    print("-----------------------------------")

    print(f"Test Type        : {test_type}")
    print(f"Target Users     : {current_users}")
    print(f"Target TPS       : {target_tps}")
    print(f"Target P95       : {target_p95} ms")
    print(f"Ramp-up          : {current_ramp_up} sec")
    print(f"Duration         : {current_duration} sec")

    print()
    print("CURRENT MODEL")
    print("-----------------------------------")

    print("Thread Group     : Classic Thread Group")
    print("Load Model       : Concurrency based")

    print()
    print("AGENT ANALYSIS")
    print("-----------------------------------")

    if test_type == "BASELINE":

        selected_group = "Classic Thread Group"

        reason = (
            "Baseline testing normally requires a small "
            "controlled number of users."
        )

    elif test_type == "LOAD" and target_tps > 0:

        selected_group = "TPS / Arrival-Rate Oriented Model"

        reason = (
            "The workload requirement specifies a target TPS. "
            "The load model should therefore control request "
            "arrival rate instead of relying only on concurrency."
        )

    elif test_type == "STRESS":

        selected_group = "Stepping / Increasing Load Model"

        reason = (
            "Stress testing requires progressively increasing "
            "load to identify the system's breaking point."
        )

    elif test_type == "SPIKE":

        selected_group = "Rapid Ramp / Arrival-Rate Model"

        reason = (
            "Spike testing requires a rapid increase in load "
            "over a short period."
        )

    elif test_type == "SOAK":

        selected_group = "Sustained Load Model"

        reason = (
            "Soak testing requires sustained workload over "
            "an extended duration."
        )

    else:

        selected_group = "Classic Thread Group"

        reason = (
            "No specific workload model requirement was detected."
        )

    print()
    print("THREAD GROUP DECISION")
    print("-----------------------------------")

    print(f"Selected Model  : {selected_group}")

    print()
    print("REASON")
    print("-----------------------------------")

    print(reason)

    print()
    print("AGENT NEXT ACTION")
    print("-----------------------------------")

    if selected_group != "Classic Thread Group":

        print("Current workload model requires adjustment.")
        print("Do NOT perform application RCA yet.")
        print("Generate the recommended workload.")
        print("Validate the generated JMX.")
        print("Execute the corrected workload.")

    else:

        print("Current workload model is acceptable.")
        print("Proceed to workload validation.")

    return {
        "test_type": test_type,
        "target_users": current_users,
        "target_tps": target_tps,
        "target_p95_ms": target_p95,
        "ramp_up_seconds": current_ramp_up,
        "duration_seconds": current_duration,
        "selected_thread_group": selected_group,
        "reason": reason
    }


if __name__ == "__main__":
    select_thread_group()