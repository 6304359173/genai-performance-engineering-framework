import xml.etree.ElementTree as ET
from pathlib import Path


JMX_FILE = Path("scripts/generated_tps_test.jmx")

BUSINESS_SAMPLERS = {
    "ProductsRequest",
    "CreateOrders",
    "GetOrders",
}


def sampler_names(hash_tree):
    """
    Find HTTP samplers inside a JMeter hashTree.
    """

    result = []

    for element in hash_tree.iter():

        if element.tag == "HTTPSamplerProxy":

            name = element.attrib.get("testname", "")

            if name:
                result.append(name)

    return result


def debug_samplers(hash_tree):

    result = []

    for element in hash_tree.iter():

        if element.tag == "DebugSampler":

            result.append(
                element.attrib.get(
                    "testname",
                    "Debug Sampler"
                )
            )

    return result


def find_thread_group_pairs(testplan_tree):

    """
    JMeter structure:

        ThreadGroup
        hashTree

        OpenModelThreadGroup
        hashTree

    The ThreadGroup and hashTree are siblings.
    """

    children = list(testplan_tree)

    pairs = []

    i = 0

    while i < len(children):

        element = children[i]

        if element.tag in (
            "ThreadGroup",
            "OpenModelThreadGroup"
        ):

            group = element

            associated_tree = None

            if i + 1 < len(children):

                next_element = children[i + 1]

                if next_element.tag == "hashTree":

                    associated_tree = next_element

            pairs.append(
                (
                    group,
                    associated_tree
                )
            )

        i += 1

    return pairs


def main():

    print("=" * 70)
    print("JMX STRUCTURE VALIDATION")
    print("=" * 70)

    if not JMX_FILE.exists():

        print(
            f"ERROR: JMX file not found: {JMX_FILE}"
        )

        return

    # ------------------------------------------------------------
    # XML validation
    # ------------------------------------------------------------

    try:

        tree = ET.parse(JMX_FILE)
        root = tree.getroot()

    except Exception as e:

        print("XML VALIDATION: FAIL")
        print(e)

        return

    print()
    print(f"JMX File: {JMX_FILE}")
    print("XML Validation: PASS")

    # ------------------------------------------------------------
    # Locate TestPlan hashTree
    # ------------------------------------------------------------

    root_hash_tree = root.find("hashTree")

    if root_hash_tree is None:

        print("ERROR: Root hashTree not found")

        return

    children = list(root_hash_tree)

    testplan_tree = None

    for i, element in enumerate(children):

        if element.tag == "TestPlan":

            if i + 1 < len(children):

                if children[i + 1].tag == "hashTree":

                    testplan_tree = children[i + 1]

            break

    if testplan_tree is None:

        print("ERROR: TestPlan hashTree not found")

        return

    # ------------------------------------------------------------
    # Find ThreadGroup/hashTree pairs
    # ------------------------------------------------------------

    pairs = find_thread_group_pairs(
        testplan_tree
    )

    print()
    print("THREAD GROUP STRUCTURE")
    print("-" * 70)

    open_model_tree = None

    for group, group_tree in pairs:

        group_name = group.attrib.get(
            "testname",
            group.tag
        )

        print()
        print(
            f"THREAD GROUP: {group_name}"
        )

        print(
            f"TYPE        : {group.tag}"
        )

        if group_tree is None:

            print(
                "ERROR: Associated hashTree not found"
            )

            continue

        samplers = sampler_names(
            group_tree
        )

        debug = debug_samplers(
            group_tree
        )

        print("HTTP SAMPLERS:")

        if samplers:

            for sampler in samplers:

                print(
                    f"  - {sampler}"
                )

        else:

            print("  NONE")

        print("DEBUG SAMPLERS:")

        if debug:

            for sampler in debug:

                print(
                    f"  - {sampler}"
                )

        else:

            print("  NONE")

        if group.tag == "OpenModelThreadGroup":

            open_model_tree = group_tree

    # ------------------------------------------------------------
    # Open Model validation
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print("OPEN MODEL VALIDATION")
    print("=" * 70)

    if open_model_tree is None:

        print(
            "Open Model Thread Group: NOT FOUND"
        )

        return

    print(
        "Open Model Thread Group: FOUND"
    )

    # Find schedule
    schedule = None

    for group, _ in pairs:

        if group.tag == "OpenModelThreadGroup":

            for element in group:

                if element.tag == "stringProp":

                    if element.attrib.get(
                        "name"
                    ) == "OpenModelThreadGroup.schedule":

                        schedule = element.text

    print(
        f"Schedule: {schedule}"
    )

    # ------------------------------------------------------------
    # Business sampler validation
    # ------------------------------------------------------------

    open_model_samplers = sampler_names(
        open_model_tree
    )

    print()
    print(
        "BUSINESS SAMPLERS UNDER OPEN MODEL:"
    )

    missing = []

    for required in BUSINESS_SAMPLERS:

        if required in open_model_samplers:

            print(
                f"  PASS - {required}"
            )

        else:

            print(
                f"  FAIL - {required}"
            )

            missing.append(required)

    # ------------------------------------------------------------
    # Debug sampler validation
    # ------------------------------------------------------------

    open_model_debug = debug_samplers(
        open_model_tree
    )

    print()
    print(
        "DEBUG SAMPLERS UNDER OPEN MODEL:"
    )

    if open_model_debug:

        for sampler in open_model_debug:

            print(
                f"  FAIL - {sampler}"
            )

    else:

        print(
            "  PASS - None"
        )

    # ------------------------------------------------------------
    # Final decision
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print("FINAL DECISION")
    print("=" * 70)

    if missing:

        print("FAIL")
        print()
        print(
            "Required business samplers are missing "
            "from the Open Model workload."
        )

        print()
        print(
            "DO NOT EXECUTE generated_tps_test.jmx"
        )

        return

    if open_model_debug:

        print("FAIL")
        print()
        print(
            "Debug Sampler exists inside the "
            "Open Model workload."
        )

        print()
        print(
            "DO NOT EXECUTE generated_tps_test.jmx"
        )

        return

    print("PASS")
    print()
    print(
        "Open Model Thread Group contains "
        "all required business samplers."
    )

    print(
        "Debug Sampler is excluded."
    )

    print()
    print(
        "Generated workload structure is ready "
        "for controlled execution."
    )


if __name__ == "__main__":

    main()