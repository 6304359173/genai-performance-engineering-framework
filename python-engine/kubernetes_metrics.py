import json
import subprocess


def run_command(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        shell=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def parse_top_nodes(output):
    lines = output.splitlines()

    if len(lines) < 2:
        return {}

    headers = lines[0].split()
    nodes = {}

    for line in lines[1:]:
        parts = line.split()

        if len(parts) < len(headers):
            continue

        nodes[parts[0]] = {
            "cpu": parts[1],
            "cpu_percent": parts[2],
            "memory": parts[3],
            "memory_percent": parts[4]
        }

    return nodes


def parse_top_pods(output):
    lines = output.splitlines()

    if len(lines) < 2:
        return {}

    pods = {}

    for line in lines[1:]:
        parts = line.split()

        if len(parts) < 3:
            continue

        pods[parts[0]] = {
            "cpu": parts[1],
            "memory": parts[2]
        }

    return pods


def get_kubernetes_metrics():
    node_output = run_command("kubectl top nodes")
    pod_output = run_command("kubectl top pods")

    return {
        "nodes": parse_top_nodes(node_output),
        "pods": parse_top_pods(pod_output)
    }


if __name__ == "__main__":
    metrics = get_kubernetes_metrics()

    print(json.dumps(metrics, indent=2))