import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

JMX_FILE = BASE_DIR / "scripts" / "ai_perf_test.jmx"
METRICS_FILE = BASE_DIR / "python-engine" / "metrics.json"


def get_jmx_text():
    with open(JMX_FILE, "r", encoding="utf-8") as f:
        return f.read()


def extract_property(text, property_name, default=None):

    pattern = (
        r'<stringProp name="' +
        re.escape(property_name) +
        r'">\$\{__P\([^,]+,([^}]+)\)\}</stringProp>'
    )

    match = re.search(pattern, text)

    if match:
        return match.group(1)

    return default


def analyze_jmx():

    text = get_jmx_text()

    users = extract_property(
        text,
        "ThreadGroup.num_threads",
        "UNKNOWN"
    )

    ramp_up = extract_property(
        text,
        "ThreadGroup.ramp_time",
        "UNKNOWN"
    )

    duration = extract_property(
        text,
        "ThreadGroup.duration",
        "UNKNOWN"
    )

    thread_group_type = "Unknown"

    if "ThreadGroup" in text:
        thread_group_type = "Classic Thread Group"

    debug_sampler_count = len(
        re.findall(
            r'(?:Debug Sampler|testname="Debug Sampler"|testname>Debug Sampler)',
            text,
            re.IGNORECASE
        )
    )

    http_sampler_count = len(
        re.findall(r'HTTPSamplerProxy', text)
    )

    return {
        "thread_group_type": thread_group_type,
        "users": users,
        "ramp_up_seconds": ramp_up,
        "duration_seconds": duration,
        "debug_sampler_count": debug_sampler_count,
        "http_sampler_count": http_sampler_count
    }


def load_metrics():

    with open(METRICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def check_workload():

    jmx = analyze_jmx()
    metrics = load_metrics()

    performance = metrics["performance_metrics"]
    sla = metrics["sla"]

    actual_tps = performance["tps"]
    target_tps = sla["required_tps"]

    actual_p95 = performance["p95_ms"]

    users = jmx["users"]

    print()
    print("===================================")
    print("       WORKLOAD ADEQUACY CHECK")
    print("===================================")

    print()
    print("JMX DESIGN")
    print("-----------------------------------")

    print(f"Thread Group       : {jmx['thread_group_type']}")
    print(f"Users              : {users}")
    print(f"Ramp-up            : {jmx['ramp_up_seconds']} sec")
    print(f"Duration           : {jmx['duration_seconds']} sec")
    print(f"HTTP Samplers      : {jmx['http_sampler_count']}")
    print(f"Debug Samplers     : {jmx['debug_sampler_count']}")

    print()
    print("PERFORMANCE")
    print("-----------------------------------")

    print(f"Actual TPS         : {actual_tps}")
    print(f"Target TPS         : {target_tps}")
    print(f"P95                : {actual_p95} ms")

    print()
    print("ADEQUACY ANALYSIS")
    print("-----------------------------------")

    # Target TPS check
    if actual_tps < target_tps:

        print("TPS Target         : NOT ACHIEVED")

    else:

        print("TPS Target         : ACHIEVED")

    # Debug sampler warning
    if jmx["debug_sampler_count"] > 0:

        print()
        print("WARNING")
        print("-----------------------------------")
        print(
            "Debug Sampler detected. "
            "Technical/debug samplers may inflate total TPS."
        )

    # Workload type assessment
    print()
    print("WORKLOAD MODEL")
    print("-----------------------------------")

    if "Classic Thread Group" in jmx["thread_group_type"]:

        print(
            "Current model is concurrency-based "
            "using a classic Thread Group."
        )

        print(
            "This is not a direct arrival-rate/TPS workload model."
        )

    # Simple concurrency/TPS observation
    try:

        numeric_users = float(users)

        if numeric_users > 0:

            observed_tps_per_user = actual_tps / numeric_users

            print()
            print(
                f"Observed TPS per user : "
                f"{observed_tps_per_user:.2f}"
            )

            theoretical_tps_from_response = (
                numeric_users /
                (actual_p95 / 1000)
            )

            print(
                "Rough concurrency/P95 capacity indicator : "
                f"{theoretical_tps_from_response:.2f} TPS"
            )

    except (ValueError, TypeError, ZeroDivisionError):

        pass

    print()
    print("AGENT DECISION")
    print("-----------------------------------")

    if actual_tps < target_tps:

        if jmx["debug_sampler_count"] > 0:

            print("THROUGHPUT FAILURE DETECTED")
            print("Workload model requires validation.")
            print("Debug Sampler may be affecting measured TPS.")
            print(
                "Next action: clean workload and validate "
                "business TPS measurement."
            )

        elif "Classic Thread Group" in jmx["thread_group_type"]:

            print("THROUGHPUT FAILURE DETECTED")
            print("Current test uses concurrency-based loading.")
            print(
                "Target TPS should be validated with an "
                "arrival-rate/throughput-oriented workload."
            )
            print(
                "Next action: evaluate JMeter Thread Group "
                "selection."
            )

        else:

            print("THROUGHPUT FAILURE DETECTED")
            print(
                "Workload adequacy requires further evidence "
                "before application RCA."
            )

    else:

        print("Workload achieved the required TPS.")
        print(
            "Application/infrastructure RCA can proceed "
            "if another SLA dimension fails."
        )


if __name__ == "__main__":
    check_workload()