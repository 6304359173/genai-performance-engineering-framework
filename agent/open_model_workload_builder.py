def find_testplan_hash_tree(root):
    """
    Find the hashTree that directly follows the TestPlan
    element in the JMeter XML hierarchy.
    """

    for parent in root.iter():

        children = list(parent)

        for i, child in enumerate(children):

            if child is not None and tag(child) == "TestPlan":

                if i + 1 < len(children):

                    following = children[i + 1]

                    if tag(following) == "hashTree":
                        return following

    return None