from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent

SOURCE_JMX = ROOT / "scripts" / "ai_perf_test.jmx"
GENERATED_JMX = ROOT / "scripts" / "generated_tps_test.jmx"

TARGET_TPS = 100
RAMP_UP = 30
DURATION = 60


# ============================================================
# READ SOURCE JMX
# ============================================================

def read_jmx():

    if not SOURCE_JMX.exists():
        raise FileNotFoundError(
            f"Source JMX not found: {SOURCE_JMX}"
        )

    return SOURCE_JMX.read_text(encoding="utf-8")


# ============================================================
# FIND TEST PLAN HASH TREE
# ============================================================

def find_test_plan_hash_tree(root):

    test_plan_tree = root.find("./hashTree")

    if test_plan_tree is None:
        raise RuntimeError(
            "Root hashTree not found."
        )

    plan_hash_tree = test_plan_tree.find("./hashTree")

    if plan_hash_tree is None:
        raise RuntimeError(
            "Test Plan hashTree not found."
        )

    return plan_hash_tree


# ============================================================
# FIND OPEN MODEL THREAD GROUP
# ============================================================

def find_open_model_group(plan_hash_tree):

    children = list(plan_hash_tree)

    for index, child in enumerate(children):

        if child.tag == "OpenModelThreadGroup":

            if index + 1 >= len(children):
                raise RuntimeError(
                    "Open Model Thread Group hashTree not found."
                )

            child_tree = children[index + 1]

            if child_tree.tag != "hashTree":
                raise RuntimeError(
                    "Open Model Thread Group hashTree not found."
                )

            return child, child_tree

    raise RuntimeError(
        "Open Model Thread Group not found."
    )


# ============================================================
# FIND CLASSIC THREAD GROUP
# ============================================================

def find_classic_thread_group(plan_hash_tree):

    children = list(plan_hash_tree)

    for index, child in enumerate(children):

        if child.tag == "ThreadGroup":

            if index + 1 >= len(children):
                raise RuntimeError(
                    "Classic Thread Group hashTree not found."
                )

            child_tree = children[index + 1]

            if child_tree.tag != "hashTree":
                raise RuntimeError(
                    "Classic Thread Group hashTree not found."
                )

            return child, child_tree

    raise RuntimeError(
        "Classic Thread Group not found."
    )


# ============================================================
# REMOVE DEBUG SAMPLERS
# ============================================================

def remove_debug_samplers(parent):

    removed = 0

    children = list(parent)

    i = 0

    while i < len(children):

        child = children[i]

        if child.tag == "DebugSampler":

            parent.remove(child)

            removed += 1

            # Remove hashTree immediately following Debug Sampler
            if i + 1 < len(children):

                next_child = children[i + 1]

                if next_child.tag == "hashTree":

                    parent.remove(next_child)

                    children.pop(i + 1)

            children.pop(i)

            continue

        # Recursively inspect nested elements
        if len(child):

            removed += remove_debug_samplers(child)

        i += 1

    return removed


# ============================================================
# REMOVE UNWANTED PERFORMANCE ELEMENTS
# ============================================================

def remove_unwanted_performance_elements(parent):

    removed_http = 0
    removed_listeners = 0
    removed_timers = 0

    children = list(parent)

    i = 0

    while i < len(children):

        child = children[i]

        # ----------------------------------------------------
        # Remove unnamed / generic HTTP Request
        # ----------------------------------------------------

        if (
            child.tag == "HTTPSamplerProxy"
            and child.get("testname") == "HTTP Request"
        ):

            parent.remove(child)

            removed_http += 1

            # Remove associated hashTree
            if i + 1 < len(children):

                next_child = children[i + 1]

                if next_child.tag == "hashTree":

                    parent.remove(next_child)

                    children.pop(i + 1)

            children.pop(i)

            continue

        # ----------------------------------------------------
        # Remove View Results Tree
        # ----------------------------------------------------

        if (
            child.tag == "ResultCollector"
            and child.get("testname") == "View Results Tree"
        ):

            parent.remove(child)

            removed_listeners += 1

            # Remove associated hashTree
            if i + 1 < len(children):

                next_child = children[i + 1]

                if next_child.tag == "hashTree":

                    parent.remove(next_child)

                    children.pop(i + 1)

            children.pop(i)

            continue

        # ----------------------------------------------------
        # Remove Constant Throughput Timer
        # ----------------------------------------------------

        if (
            child.tag == "ConstantThroughputTimer"
            and child.get("testname") == "Constant Throughput Timer"
        ):

            parent.remove(child)

            removed_timers += 1

            # Remove associated hashTree
            if i + 1 < len(children):

                next_child = children[i + 1]

                if next_child.tag == "hashTree":

                    parent.remove(next_child)

                    children.pop(i + 1)

            children.pop(i)

            continue

        # ----------------------------------------------------
        # Recursively clean nested structures
        # ----------------------------------------------------

        if len(child):

            (
                nested_http,
                nested_listeners,
                nested_timers
            ) = remove_unwanted_performance_elements(child)

            removed_http += nested_http
            removed_listeners += nested_listeners
            removed_timers += nested_timers

        i += 1

    return (
        removed_http,
        removed_listeners,
        removed_timers
    )


# ============================================================
# COUNT HTTP SAMPLERS
# ============================================================

def get_http_samplers(parent):

    return parent.findall(".//HTTPSamplerProxy")


# ============================================================
# GET SAMPLER NAMES
# ============================================================

def get_sampler_names(parent):

    samplers = get_http_samplers(parent)

    return [
        sampler.get("testname", "")
        for sampler in samplers
    ]


# ============================================================
# GENERATE WORKLOAD
# ============================================================

def generate_workload(original_text):

    root = ET.fromstring(original_text)

    plan_hash_tree = find_test_plan_hash_tree(root)

    classic_group, classic_tree = find_classic_thread_group(
        plan_hash_tree
    )

    open_model_group, open_model_tree = find_open_model_group(
        plan_hash_tree
    )

    # --------------------------------------------------------
    # Clear existing Open Model children
    # --------------------------------------------------------

    for child in list(open_model_tree):

        open_model_tree.remove(child)

    # --------------------------------------------------------
    # Move complete Classic Thread Group workload
    # into Open Model Thread Group
    # --------------------------------------------------------

    for child in list(classic_tree):

        classic_tree.remove(child)

        open_model_tree.append(child)

    # --------------------------------------------------------
    # Remove Debug Samplers
    # --------------------------------------------------------

    debug_removed = remove_debug_samplers(
        open_model_tree
    )

    # --------------------------------------------------------
    # Remove unwanted performance elements
    # --------------------------------------------------------

    (
        unwanted_http_removed,
        listeners_removed,
        timers_removed
    ) = remove_unwanted_performance_elements(
        open_model_tree
    )

    # --------------------------------------------------------
    # Remove Classic Thread Group
    # --------------------------------------------------------

    plan_hash_tree.remove(classic_group)

    plan_hash_tree.remove(classic_tree)

    # --------------------------------------------------------
    # Create Open Model schedule
    # --------------------------------------------------------

    schedule = (
        f"rate(0/sec) "
        f"random_arrivals({RAMP_UP} sec) "
        f"rate({TARGET_TPS}/sec) "
        f"random_arrivals({DURATION} sec)"
    )

    schedule_property = open_model_group.find(
        "stringProp[@name='OpenModelThreadGroup.schedule']"
    )

    if schedule_property is None:

        schedule_property = ET.SubElement(
            open_model_group,
            "stringProp",
            {
                "name":
                "OpenModelThreadGroup.schedule"
            }
        )

    schedule_property.text = schedule

    # --------------------------------------------------------
    # Save generated JMX
    # --------------------------------------------------------

    tree = ET.ElementTree(root)

    ET.indent(tree, space="  ")

    tree.write(
        GENERATED_JMX,
        encoding="utf-8",
        xml_declaration=True
    )

    return (
        schedule,
        debug_removed,
        unwanted_http_removed,
        listeners_removed,
        timers_removed
    )


# ============================================================
# VALIDATE GENERATED JMX
# ============================================================

def validate_jmx():

    if not GENERATED_JMX.exists():

        return False, (
            "Generated JMX does not exist."
        )

    try:

        tree = ET.parse(GENERATED_JMX)

        root = tree.getroot()

        plan_hash_tree = find_test_plan_hash_tree(root)

        # ----------------------------------------------------
        # Validate Open Model Thread Group
        # ----------------------------------------------------

        open_model_groups = plan_hash_tree.findall(
            "OpenModelThreadGroup"
        )

        if len(open_model_groups) != 1:

            return False, (
                "Expected exactly one Open Model "
                f"Thread Group, found "
                f"{len(open_model_groups)}."
            )

        open_model_group, open_model_tree = (
            find_open_model_group(
                plan_hash_tree
            )
        )

        # ----------------------------------------------------
        # Validate Classic Thread Group removal
        # ----------------------------------------------------

        classic_groups = plan_hash_tree.findall(
            "ThreadGroup"
        )

        if classic_groups:

            return False, (
                "Classic Thread Group still exists."
            )

        # ----------------------------------------------------
        # Validate HTTP samplers
        # ----------------------------------------------------

        samplers = get_http_samplers(
            open_model_tree
        )

        if not samplers:

            return False, (
                "No HTTP samplers found under "
                "Open Model Thread Group."
            )

        sampler_names = get_sampler_names(
            open_model_tree
        )

        # ----------------------------------------------------
        # Expected business samplers
        # ----------------------------------------------------

        expected = {
            "ProductsRequest",
            "CreateOrders",
            "GetOrders"
        }

        actual = set(sampler_names)

        missing = expected - actual

        if missing:

            return False, (
                "Missing expected business samplers: "
                f"{sorted(missing)}"
            )

        # ----------------------------------------------------
        # Check for generic HTTP Request
        # ----------------------------------------------------

        generic_http = [
            name
            for name in sampler_names
            if name == "HTTP Request"
        ]

        if generic_http:

            return False, (
                "Generic HTTP Request still exists."
            )

        # ----------------------------------------------------
        # Check Debug Sampler
        # ----------------------------------------------------

        debug_samplers = open_model_tree.findall(
            ".//DebugSampler"
        )

        if debug_samplers:

            return False, (
                "Debug Sampler still exists."
            )

        # ----------------------------------------------------
        # Check View Results Tree
        # ----------------------------------------------------

        view_results = open_model_tree.findall(
            ".//ResultCollector"
        )

        for collector in view_results:

            if collector.get("testname") == "View Results Tree":

                return False, (
                    "View Results Tree still exists."
                )

        # ----------------------------------------------------
        # Check Constant Throughput Timer
        # ----------------------------------------------------

        throughput_timers = open_model_tree.findall(
            ".//ConstantThroughputTimer"
        )

        if throughput_timers:

            return False, (
                "Constant Throughput Timer still exists."
            )

        # ----------------------------------------------------
        # Check schedule
        # ----------------------------------------------------

        schedule_property = open_model_group.find(
            "stringProp[@name='OpenModelThreadGroup.schedule']"
        )

        if schedule_property is None:

            return False, (
                "Open Model schedule not found."
            )

        # ----------------------------------------------------
        # Validation success
        # ----------------------------------------------------

        message = (
            "XML structure is valid.\n"
            f"Business HTTP Samplers : {len(samplers)}\n"
            f"Sampler Names           : {', '.join(sampler_names)}\n"
            f"Debug Samplers          : {len(debug_samplers)}\n"
            f"View Results Tree       : 0\n"
            f"Constant Throughput     : 0\n"
            f"Classic Thread Groups   : 0\n"
            f"Schedule                : "
            f"{schedule_property.text}"
        )

        return True, message

    except ET.ParseError as exc:

        return False, (
            f"XML validation failed: {exc}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("       AI JMX WORKLOAD GENERATOR")
    print("=" * 60)

    print()
    print(f"Source JMX    : {SOURCE_JMX}")
    print(f"Generated JMX : {GENERATED_JMX}")

    original = read_jmx()

    print()
    print("WORKLOAD REQUIREMENT")
    print("----------------------------------------")

    print(
        f"Target Arrival Rate : "
        f"{TARGET_TPS}/sec"
    )

    print(
        f"Ramp / Setup        : "
        f"{RAMP_UP} sec"
    )

    print(
        f"Test Duration       : "
        f"{DURATION} sec"
    )

    print()
    print("AGENT DECISION")
    print("----------------------------------------")

    print(
        "Using Open Model Thread Group."
    )

    print(
        "Classic Thread Group will be removed."
    )

    print(
        "Business HTTP flow will run under Open Model."
    )

    print(
        "Debug Sampler will be removed."
    )

    print(
        "Generic HTTP Request will be removed."
    )

    print(
        "View Results Tree will be removed."
    )

    print(
        "Constant Throughput Timer will be removed."
    )

    print(
        "Original source JMX will NOT be modified."
    )

    (
        schedule,
        debug_removed,
        unwanted_http_removed,
        listeners_removed,
        timers_removed
    ) = generate_workload(original)

    print()
    print("GENERATED OPEN MODEL SCHEDULE")
    print("----------------------------------------")

    print(schedule)

    print()
    print("PERFORMANCE TEST CLEANUP")
    print("----------------------------------------")

    print(
        f"Debug Samplers removed       : "
        f"{debug_removed}"
    )

    print(
        f"Generic HTTP Requests removed: "
        f"{unwanted_http_removed}"
    )

    print(
        f"View Results Tree removed    : "
        f"{listeners_removed}"
    )

    print(
        f"Throughput Timers removed    : "
        f"{timers_removed}"
    )

    valid, message = validate_jmx()

    print()
    print("JMX VALIDATION")
    print("----------------------------------------")

    print(message)

    if not valid:

        print()
        print("GENERATION FAILED")

        return

    print()
    print("WORKLOAD GENERATION SUCCESSFUL")
    print("----------------------------------------")

    print(
        f"Generated JMX: "
        f"{GENERATED_JMX}"
    )

    print()
    print("SAFETY CHECK")
    print("----------------------------------------")

    print(
        "Original ai_perf_test.jmx was NOT modified."
    )

    print()
    print("NEXT STEPS")
    print("----------------------------------------")

    print("1. Inspect generated JMX")

    print("2. Execute JMeter")

    print("3. Verify actual arrival rate")

    print("4. Analyze P95 / P99")

    print("5. Analyze errors")

    print("6. Evaluate SLA / SLO")


if __name__ == "__main__":
    main()