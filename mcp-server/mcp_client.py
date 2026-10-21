import asyncio
import json
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ============================================================
# Paths
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

SERVER_FILE = os.path.join(
    BASE_DIR,
    "mcp-server",
    "performance_mcp.py"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "ai-engine",
    "mcp_rca_evidence.json"
)


# ============================================================
# MCP Client
# ============================================================

async def main():

    print("====================================")
    print(" AI Performance MCP Client")
    print("====================================")
    print()

    print(f"MCP Server: {SERVER_FILE}")
    print()

    # --------------------------------------------------------
    # MCP server configuration
    # --------------------------------------------------------

    server_params = StdioServerParameters(
        command="python",
        args=[SERVER_FILE],
        env=None
    )

    # --------------------------------------------------------
    # Connect to MCP server
    # --------------------------------------------------------

    async with stdio_client(server_params) as (
        read_stream,
        write_stream
    ):

        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            # ------------------------------------------------
            # Initialize MCP connection
            # ------------------------------------------------

            await session.initialize()

            print("MCP connection initialized.")
            print()

            # ------------------------------------------------
            # Discover available MCP tools
            # ------------------------------------------------

            tools = await session.list_tools()

            print("Available MCP tools:")

            for tool in tools.tools:
                print(f" - {tool.name}")

            print()

            # ------------------------------------------------
            # Call RCA evidence tool
            # ------------------------------------------------

            result = await session.call_tool(
                "get_rca_evidence",
                arguments={}
            )

            print("get_rca_evidence() executed.")
            print()

            # ------------------------------------------------
            # Call Kubernetes metrics tool
            # ------------------------------------------------

            k8s_result = await session.call_tool(
                "get_kubernetes_metrics",
                arguments={}
            )

            print("get_kubernetes_metrics() executed.")
            print()

            # ------------------------------------------------
            # Extract Kubernetes metrics
            # ------------------------------------------------

            kubernetes_metrics = {}

            for content in k8s_result.content:

                if hasattr(content, "text"):

                    try:

                        kubernetes_metrics = json.loads(
                            content.text
                        )

                    except json.JSONDecodeError:

                        kubernetes_metrics = {
                            "raw_response": content.text
                        }

            # ------------------------------------------------
            # Extract RCA evidence
            # ------------------------------------------------

            evidence = {}

            for content in result.content:

                if hasattr(content, "text"):

                    try:

                        evidence = json.loads(
                            content.text
                        )

                    except json.JSONDecodeError:

                        evidence = {
                            "raw_response": content.text
                        }

            # ------------------------------------------------
            # Add Kubernetes metrics to RCA evidence
            # ------------------------------------------------

            if "evidence" in evidence:

                evidence["evidence"][
                    "kubernetes_metrics"
                ] = kubernetes_metrics

            # ------------------------------------------------
            # Save combined evidence
            # ------------------------------------------------

            os.makedirs(
                os.path.dirname(OUTPUT_FILE),
                exist_ok=True
            )

            with open(
                OUTPUT_FILE,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    evidence,
                    file,
                    indent=2
                )

            # ------------------------------------------------
            # Completion message
            # ------------------------------------------------

            print("MCP evidence saved.")
            print()

            print(f"Output: {OUTPUT_FILE}")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())