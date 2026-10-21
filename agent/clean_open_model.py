import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path


SOURCE = Path("scripts/ai_perf_test.jmx")
OUTPUT = Path("scripts/generated_tps_test.jmx")


def find_element(root, tag, testname=None):
    """
    Recursively find an XML element by tag and optional testname.
    """
    for elem in root.iter():
        if elem.tag == tag:
            if testname is None or elem.get("testname") == testname:
                return elem
    return None


def find_parent_and_index(root, target):
    """
    Find the parent XML element and index of target.
    """
    for parent in root.iter():
        children = list(parent)

        for index, child in enumerate(children):
            if child is target:
                return parent, index

    return None, None


def find_paired_hash_tree(root, target):
    """
    JMeter normally stores:

        ThreadGroup
        hashTree

    as sibling elements.

    This function finds the target and its following hashTree.
    """
    parent, index = find_parent_and_index(root, target)

    if parent is None:
        return None, None, None

    children = list(parent)

    if index + 1 < len(children):
        next_element = children[index + 1]

        if next_element.tag == "hashTree":
            return parent, index, next_element

    return parent, index, None


def get_http_samplers(hash_tree):
    """
    Return HTTP samplers directly contained anywhere
    inside the supplied JMeter hashTree.
    """
    samplers = []

    if hash_tree is None:
        return samplers

    for elem in hash_tree.iter():

        if elem.tag == "HTTPSamplerProxy":
            name = elem.get("testname", "")

            if name:
                samplers.append(elem)

    return samplers


def get_debug_samplers(hash_tree):
    """
    Find Debug Samplers.
    """
    result = []

    if hash_tree is None:
        return result

    for elem in hash_tree.iter():

        if elem.tag == "DebugSampler":
            result.append(elem)

    return result


def get_throughput_controllers(hash_tree):
    result = []

    if hash_tree is None:
        return result

    for elem in hash_tree.iter():

        if elem.tag == "ThroughputController":
            result.append(elem)

    return result


def get_constant_throughput_timers(hash_tree):
    result = []

    if hash_tree is None:
        return result

    for elem in hash_tree.iter():

        if elem.tag == "ConstantThroughputTimer":
            result.append(elem)

    return result


def remove_element_with_hash_tree(parent_hash_tree, element):
    """
    Remove a JMeter element and its paired hashTree.

    Example:

        DebugSampler
        hashTree

    Both are removed.
    """

    parent, index = find_parent_and_index(parent_hash_tree, element)

    if parent is None:
        return

    children = list(parent)

    # Remove element first
    parent.remove(element)

    # The original index now points to the following hashTree
    if index < len(list(parent)):

        possible_hash_tree = list(parent)[index]

        if possible_hash_tree.tag == "hashTree":
            parent.remove(possible_hash_tree)


def remove_by_tag(parent_hash_tree, tag):
    """
    Remove all matching elements and their paired hashTree.
    """

    while True:

        found = None

        for elem in parent_hash_tree.iter():

            if elem.tag == tag:
                found = elem
                break

        if found is None:
            break

        remove_element_with_hash_tree(parent_hash_tree, found)


def find_testplan_hash_tree(root):
    """
    Find the hashTree that contains the ThreadGroup
    and OpenModelThreadGroup.
    """

    for candidate in root.iter():

        if candidate.tag != "hashTree":
            continue

        has_thread_group = False
        has_open_model = False

        for child in candidate.iter():

            if child.tag == "ThreadGroup":
                has_thread_group = True

            if child.tag == "OpenModelThreadGroup":
                has_open_model = True

        if has_thread_group or has_open_model:
            return candidate

    return None


def create_clean_business_workload(classic_hash_tree):
    """
    Create a clean copy containing only:

        HTTP Request Defaults
        ProductsRequest
        CreateOrders
            Header Manager
            JSON Extractor
        GetOrders

    We intentionally do NOT copy:

        DebugSampler
        ThroughputController
        ConstantThroughputTimer
        BackendListener
        ResultCollector
        technical HTTP Request
        other technical components
    """

    new_tree = ET.Element("hashTree")

    # ---------------------------------------------------------
    # HTTP Request Defaults
    # ---------------------------------------------------------

    http_defaults = None

    for elem in classic_hash_tree:

        if elem.tag == "ConfigTestElement":
            name = elem.get("testname", "")

            if name == "HTTP Request Defaults":
                http_defaults = elem
                break

    if http_defaults is not None:

        new_tree.append(deepcopy(http_defaults))

        # JMeter ConfigTestElement requires its paired hashTree
        new_tree.append(ET.Element("hashTree"))

    # ---------------------------------------------------------
    # Find business samplers
    # ---------------------------------------------------------

    wanted = {
        "ProductsRequest",
        "CreateOrders",
        "GetOrders"
    }

    children = list(classic_hash_tree)

    for index, child in enumerate(children):

        if child.tag != "HTTPSamplerProxy":
            continue

        sampler_name = child.get("testname", "")

        if sampler_name not in wanted:
            continue

        # Add sampler
        new_tree.append(deepcopy(child))

        # Find the sampler's paired hashTree
        if index + 1 < len(children):

            paired = children[index + 1]

            if paired.tag == "hashTree":

                if sampler_name == "CreateOrders":

                    # CreateOrders needs:
                    # HeaderManager
                    # JSONPostProcessor
                    #
                    # Copy only these supporting components.

                    support_tree = ET.Element("hashTree")

                    for support_child in list(paired):

                        if support_child.tag == "HeaderManager":

                            support_tree.append(
                                deepcopy(support_child)
                            )

                            support_tree.append(
                                ET.Element("hashTree")
                            )

                        elif support_child.tag == "JSONPostProcessor":

                            support_tree.append(
                                deepcopy(support_child)
                            )

                            support_tree.append(
                                ET.Element("hashTree")
                            )

                    new_tree.append(support_tree)

                else:

                    # Other samplers do not need additional
                    # technical components.
                    new_tree.append(
                        ET.Element("hashTree")
                    )

            else:

                new_tree.append(
                    ET.Element("hashTree")
                )

        else:

            new_tree.append(
                ET.Element("hashTree")
            )

    return new_tree


def set_open_model_schedule(open_model):
    """
    Set controlled workload schedule.
    """

    schedule = "rate(100/sec) pause(30sec) rate(100/sec) pause(60sec)"

    for child in open_model:

        if (
            child.tag == "stringProp"
            and child.get("name")
            == "OpenModelThreadGroup.schedule"
        ):

            child.text = schedule
            return schedule

    # If schedule does not exist, create it.
    prop = ET.Element(
        "stringProp",
        {
            "name": "OpenModelThreadGroup.schedule"
        }
    )

    prop.text = schedule

    open_model.insert(0, prop)

    return schedule


def remove_existing_open_model_hash_tree(open_model_hash_tree):
    """
    Remove everything currently under Open Model.
    """

    for child in list(open_model_hash_tree):
        open_model_hash_tree.remove(child)


def pretty_xml(element, level=0):
    """
    Simple XML indentation for readable JMX.
    """

    indent = "\n" + level * "  "

    if len(element):

        if not element.text or not element.text.strip():
            element.text = indent + "  "

        for child in element:

            pretty_xml(child, level + 1)

            if not child.tail or not child.tail.strip():
                child.tail = indent + "  "

        if not element[-1].tail or not element[-1].tail.strip():
            element[-1].tail = indent

    else:

        if level and (not element.tail or not element.tail.strip()):
            element.tail = indent


def validate_xml(path):
    try:

        ET.parse(path)

        print("GENERATED XML VALIDATION: PASS")

        return True

    except Exception as exc:

        print("GENERATED XML VALIDATION: FAIL")
        print(exc)

        return False


def main():

    print()
    print("=" * 70)
    print("CLEAN OPEN MODEL WORKLOAD GENERATOR")
    print("=" * 70)

    print(f"Source : {SOURCE}")
    print(f"Output : {OUTPUT}")

    if not SOURCE.exists():

        raise FileNotFoundError(
            f"Source JMX not found: {SOURCE}"
        )

    # ---------------------------------------------------------
    # Load source
    # ---------------------------------------------------------

    tree = ET.parse(SOURCE)
    root = tree.getroot()

    print()
    print("SOURCE XML VALIDATION: PASS")

    # ---------------------------------------------------------
    # Find Classic Thread Group
    # ---------------------------------------------------------

    classic = find_element(
        root,
        "ThreadGroup",
        "Thread Group"
    )

    if classic is None:

        print()
        print("ERROR: Classic Thread Group not found.")

        print()
        print("Detected Thread Groups:")

        for elem in root.iter():

            if elem.tag in (
                "ThreadGroup",
                "OpenModelThreadGroup"
            ):

                print(
                    f"  {elem.tag} -> "
                    f"{elem.get('testname')}"
                )

        raise RuntimeError(
            "Classic Thread Group not found"
        )

    # ---------------------------------------------------------
    # Find Open Model Thread Group
    # ---------------------------------------------------------

    open_model = find_element(
        root,
        "OpenModelThreadGroup",
        "Open Model Thread Group"
    )

    if open_model is None:

        raise RuntimeError(
            "Open Model Thread Group not found"
        )

    print()
    print("JMeter elements found:")
    print(
        f"  Classic Thread Group : "
        f"{classic.get('testname')}"
    )
    print(
        f"  Open Model Thread Group : "
        f"{open_model.get('testname')}"
    )

    # ---------------------------------------------------------
    # Find Classic paired hashTree
    # ---------------------------------------------------------

    classic_parent, classic_index, classic_hash_tree = (
        find_paired_hash_tree(root, classic)
    )

    if classic_hash_tree is None:

        raise RuntimeError(
            "Classic Thread Group paired hashTree not found"
        )

    # ---------------------------------------------------------
    # Find Open Model paired hashTree
    # ---------------------------------------------------------

    open_parent, open_index, open_hash_tree = (
        find_paired_hash_tree(root, open_model)
    )

    if open_hash_tree is None:

        raise RuntimeError(
            "Open Model Thread Group paired hashTree not found"
        )

    print()
    print("JMeter hierarchy:")
    print("  Classic Thread Group       : FOUND")
    print("  Classic paired hashTree    : FOUND")
    print("  Open Model Thread Group    : FOUND")
    print("  Open Model paired hashTree : FOUND")

    # ---------------------------------------------------------
    # Analyze current classic workload
    # ---------------------------------------------------------

    current_samplers = get_http_samplers(
        classic_hash_tree
    )

    print()
    print("CURRENT CLASSIC WORKLOAD")

    print(
        f"HTTP Samplers : "
        f"{len(current_samplers)}"
    )

    for sampler in current_samplers:

        print(
            f"  - "
            f"{sampler.get('testname')}"
        )

    debug_count = len(
        get_debug_samplers(classic_hash_tree)
    )

    throughput_count = len(
        get_throughput_controllers(classic_hash_tree)
    )

    timer_count = len(
        get_constant_throughput_timers(classic_hash_tree)
    )

    print(
        f"Debug Samplers            : "
        f"{debug_count}"
    )

    print(
        f"Throughput Controllers    : "
        f"{throughput_count}"
    )

    print(
        f"Constant Throughput Timer : "
        f"{timer_count}"
    )

    # ---------------------------------------------------------
    # Disable Classic Thread Group
    # ---------------------------------------------------------

    classic.set(
        "enabled",
        "false"
    )

    print()
    print(
        "Classic Thread Group: "
        "DISABLED in generated JMX"
    )

    # ---------------------------------------------------------
    # Build clean business workload
    # ---------------------------------------------------------

    clean_tree = create_clean_business_workload(
        classic_hash_tree
    )

    # ---------------------------------------------------------
    # Clear existing Open Model hashTree
    # ---------------------------------------------------------

    remove_existing_open_model_hash_tree(
        open_hash_tree
    )

    # ---------------------------------------------------------
    # Copy clean workload
    # ---------------------------------------------------------

    for child in list(clean_tree):

        open_hash_tree.append(child)

    # ---------------------------------------------------------
    # Update schedule
    # ---------------------------------------------------------

    schedule = set_open_model_schedule(
        open_model
    )

    print()
    print("OPEN MODEL SCHEDULE")

    print(
        f"  {schedule}"
    )

    # ---------------------------------------------------------
    # Check resulting Open Model workload
    # ---------------------------------------------------------

    open_samplers = get_http_samplers(
        open_hash_tree
    )

    open_debug = get_debug_samplers(
        open_hash_tree
    )

    open_throughput = get_throughput_controllers(
        open_hash_tree
    )

    open_timers = get_constant_throughput_timers(
        open_hash_tree
    )

    print()
    print("GENERATED OPEN MODEL WORKLOAD")

    print(
        f"HTTP Samplers : "
        f"{len(open_samplers)}"
    )

    for sampler in open_samplers:

        print(
            f"  - "
            f"{sampler.get('testname')}"
        )

    print(
        f"Debug Samplers : "
        f"{len(open_debug)}"
    )

    print(
        f"Throughput Controllers : "
        f"{len(open_throughput)}"
    )

    print(
        f"Constant Throughput Timers : "
        f"{len(open_timers)}"
    )

    # ---------------------------------------------------------
    # Safety checks
    # ---------------------------------------------------------

    expected = {
        "ProductsRequest",
        "CreateOrders",
        "GetOrders"
    }

    actual = {
        sampler.get("testname")
        for sampler in open_samplers
    }

    missing = expected - actual

    if missing:

        raise RuntimeError(
            "Missing business samplers: "
            + ", ".join(sorted(missing))
        )

    if open_debug:

        raise RuntimeError(
            "DebugSampler found under Open Model"
        )

    if open_throughput:

        raise RuntimeError(
            "ThroughputController found under Open Model"
        )

    if open_timers:

        raise RuntimeError(
            "ConstantThroughputTimer found under Open Model"
        )

    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    pretty_xml(root)

    tree.write(
        OUTPUT,
        encoding="UTF-8",
        xml_declaration=True
    )

    # ---------------------------------------------------------
    # Final validation
    # ---------------------------------------------------------

    if not validate_xml(OUTPUT):

        raise RuntimeError(
            "Generated JMX XML validation failed"
        )

    print()
    print("=" * 70)
    print("GENERATION SUCCESS")
    print("=" * 70)

    print(
        f"Generated JMX : {OUTPUT}"
    )

    print()
    print("OPEN MODEL CONTENT")

    print(
        "  1. HTTP Request Defaults"
    )

    print(
        "  2. ProductsRequest"
    )

    print(
        "  3. CreateOrders"
    )

    print(
        "       -> Header Manager"
    )

    print(
        "       -> JSON Extractor"
    )

    print(
        "  4. GetOrders"
    )

    print()
    print("EXCLUDED FROM OPEN MODEL")

    print(
        "  - Debug Sampler"
    )

    print(
        "  - Throughput Controller"
    )

    print(
        "  - Constant Throughput Timer"
    )

    print(
        "  - Technical HTTP Request"
    )

    print()
    print(
        "Original ai_perf_test.jmx was NOT modified."
    )

    print()


if __name__ == "__main__":

    main()