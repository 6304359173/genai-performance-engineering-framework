import csv
import json
import os
import statistics


# ---------------------------------------
# File locations
# ---------------------------------------

WORKSPACE = os.environ.get(
    "WORKSPACE",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

JTL_FILE = os.path.join(
    WORKSPACE,
    "results",
    "generated_tps_results.jtl"
)

OUTPUT_FILE = os.path.join(
    WORKSPACE,
    "python-engine",
    "metrics.json"
)


# ---------------------------------------
# SLA Configuration
# ---------------------------------------

SLA = {
    "p95_ms": 2000,
    "tps": 100,
    "error_rate_percent": 1
}


# ---------------------------------------
# Workload Configuration
# ---------------------------------------

WORKLOAD = {
    "business_transaction_label": "ProductsRequest",

    # ProductsRequest + CreateOrders + GetOrders
    "http_requests_per_business_transaction": 3,

    # Open Model schedule:
    # 30 sec ramp
    # 60 sec steady state
    "steady_state_start_seconds": 30,
    "steady_state_duration_seconds": 60
}


# ---------------------------------------
# Percentile calculation
# ---------------------------------------

def percentile(values, percentile):

    if not values:
        return 0

    values = sorted(values)

    index = (len(values) - 1) * percentile / 100

    lower = int(index)
    upper = lower + 1

    if upper >= len(values):
        return values[lower]

    weight = index - lower

    return values[lower] + (
        values[upper] - values[lower]
    ) * weight


# ---------------------------------------
# Read JMeter JTL
# ---------------------------------------

def read_jtl():

    if not os.path.exists(JTL_FILE):

        raise FileNotFoundError(
            f"JTL file not found: {JTL_FILE}"
        )

    rows = []

    with open(
        JTL_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            rows.append(row)

    return rows


# ---------------------------------------
# Analyze performance results
# ---------------------------------------

def analyze(rows):

    if not rows:

        raise ValueError(
            "JTL file contains no results."
        )

    response_times = []

    successful = 0
    failed = 0

    timestamps = []

    # -----------------------------------
    # Transaction statistics
    # -----------------------------------

    transaction_stats = {}

    # -----------------------------------
    # Failure analysis
    # -----------------------------------

    response_code_stats = {}

    for row in rows:

        elapsed = float(row["elapsed"])

        response_times.append(elapsed)

        timestamp = int(row["timeStamp"])

        timestamps.append(timestamp)

        success = (
            row["success"].lower() == "true"
        )

        transaction = (
            row.get("label")
            or row.get("sampler")
            or "Unknown"
        )

        response_code = (
            row.get("responseCode")
            or "UNKNOWN"
        )

        # --------------------------------
        # Overall success/failure
        # --------------------------------

        if success:
            successful += 1
        else:
            failed += 1

        # --------------------------------
        # Transaction statistics
        # --------------------------------

        if transaction not in transaction_stats:

            transaction_stats[transaction] = {
                "response_times": [],
                "timestamps": [],
                "total": 0,
                "successful": 0,
                "failed": 0
            }

        transaction_stats[
            transaction
        ]["response_times"].append(elapsed)

        transaction_stats[
            transaction
        ]["timestamps"].append(timestamp)

        transaction_stats[
            transaction
        ]["total"] += 1

        if success:

            transaction_stats[
                transaction
            ]["successful"] += 1

        else:

            transaction_stats[
                transaction
            ]["failed"] += 1

        # --------------------------------
        # Response-code statistics
        # --------------------------------

        if response_code not in response_code_stats:

            response_code_stats[response_code] = {
                "total": 0,
                "successful": 0,
                "failed": 0
            }

        response_code_stats[
            response_code
        ]["total"] += 1

        if success:

            response_code_stats[
                response_code
            ]["successful"] += 1

        else:

            response_code_stats[
                response_code
            ]["failed"] += 1


    # -----------------------------------
    # Basic overall metrics
    # -----------------------------------

    total = len(rows)

    average = statistics.mean(response_times)

    minimum = min(response_times)

    maximum = max(response_times)

    p90 = percentile(
        response_times,
        90
    )

    p95 = percentile(
        response_times,
        95
    )

    p99 = percentile(
        response_times,
        99
    )


    # -----------------------------------
    # Test duration
    # -----------------------------------

    start_time = min(timestamps)

    end_time = max(timestamps)

    duration_seconds = (
        end_time - start_time
    ) / 1000

    if duration_seconds <= 0:
        duration_seconds = 1


    # -----------------------------------
    # Overall throughput
    # -----------------------------------

    debug_total = (
        transaction_stats
        .get("Debug Sampler", {})
        .get("total", 0)
    )

    http_business_samples = (
        total - debug_total
    )

    # Overall HTTP request rate
    overall_http_request_rate = (
        http_business_samples
        / duration_seconds
    )


    # -----------------------------------
    # Overall Business TPS
    # -----------------------------------

    business_transaction_label = (
        WORKLOAD[
            "business_transaction_label"
        ]
    )

    business_transaction_stats = (
        transaction_stats.get(
            business_transaction_label,
            {}
        )
    )

    business_total = (
        business_transaction_stats.get(
            "total",
            0
        )
    )

    overall_business_tps = (
        business_total
        / duration_seconds
    )


    # -----------------------------------
    # Steady-State Business TPS
    # -----------------------------------

    steady_state_start = (
        start_time
        + (
            WORKLOAD[
                "steady_state_start_seconds"
            ] * 1000
        )
    )

    requested_steady_state_end = (
        steady_state_start
        + (
            WORKLOAD[
                "steady_state_duration_seconds"
            ] * 1000
        )
    )

    steady_state_end = min(
        requested_steady_state_end,
        end_time
    )

    steady_state_window_seconds = (
        steady_state_end
        - steady_state_start
    ) / 1000

    if steady_state_window_seconds <= 0:

        steady_state_window_seconds = 1


    # ProductsRequest represents one
    # business transaction/arrival.

    steady_state_business_rows = [

        row

        for row in rows

        if (
            row.get("label")
            == business_transaction_label

            and

            steady_state_start
            <= int(row["timeStamp"])
            <= steady_state_end
        )
    ]

    steady_state_business_transactions = len(
        steady_state_business_rows
    )

    steady_state_business_tps = (
        steady_state_business_transactions
        / steady_state_window_seconds
    )


    # -----------------------------------
    # Steady-State HTTP Rate
    # -----------------------------------

    steady_state_http_request_rate = (

        steady_state_business_tps

        *

        WORKLOAD[
            "http_requests_per_business_transaction"
        ]
    )


    # -----------------------------------
    # Overall error rate
    # -----------------------------------

    error_rate = (
        failed / total
    ) * 100


    # -----------------------------------
    # Build transaction summary
    # -----------------------------------

    transaction_summary = {}

    for transaction, stats in (
        transaction_stats.items()
    ):

        times = stats[
            "response_times"
        ]

        transaction_start = min(
            stats["timestamps"]
        )

        transaction_end = max(
            stats["timestamps"]
        )

        transaction_duration = (
            transaction_end
            - transaction_start
        ) / 1000

        if transaction_duration <= 0:
            transaction_duration = 1

        transaction_tps = (
            stats["total"]
            / transaction_duration
        )

        transaction_error_rate = (
            stats["failed"]
            / stats["total"]
        ) * 100

        transaction_summary[
            transaction
        ] = {

            "total":
                stats["total"],

            "successful":
                stats["successful"],

            "failed":
                stats["failed"],

            "error_rate_percent":
                round(
                    transaction_error_rate,
                    2
                ),

            "average_response_time_ms":
                round(
                    statistics.mean(times),
                    2
                ),

            "min_response_time_ms":
                round(
                    min(times),
                    2
                ),

            "max_response_time_ms":
                round(
                    max(times),
                    2
                ),

            "p90_ms":
                round(
                    percentile(times, 90),
                    2
                ),

            "p95_ms":
                round(
                    percentile(times, 95),
                    2
                ),

            "p99_ms":
                round(
                    percentile(times, 99),
                    2
                ),

            "tps":
                round(
                    transaction_tps,
                    2
                )
        }


    # -----------------------------------
    # Response-code error rates
    # -----------------------------------

    for code, stats in (
        response_code_stats.items()
    ):

        stats[
            "error_rate_percent"
        ] = round(

            (
                stats["failed"]
                / stats["total"]
            ) * 100,

            2
        )


    # -----------------------------------
    # SLA validation
    # -----------------------------------

    p95_pass = (
        p95 < SLA["p95_ms"]
    )

    # IMPORTANT:
    # SLA TPS is steady-state BUSINESS TPS.
    tps_pass = (
        steady_state_business_tps
        >= SLA["tps"]
    )

    error_pass = (
        error_rate
        < SLA["error_rate_percent"]
    )

    overall_pass = (
        p95_pass
        and
        tps_pass
        and
        error_pass
    )


    # -----------------------------------
    # Final metrics JSON
    # -----------------------------------

    metrics = {

        # --------------------------------
        # Test summary
        # --------------------------------

        "test_summary": {

            "total_requests":
                total,

            "successful_requests":
                successful,

            "failed_requests":
                failed,

            "test_duration_seconds":
                round(
                    duration_seconds,
                    2
                )
        },


        # --------------------------------
        # Performance metrics
        # --------------------------------

        "performance_metrics": {

            "average_response_time_ms":
                round(
                    average,
                    2
                ),

            "min_response_time_ms":
                round(
                    minimum,
                    2
                ),

            "max_response_time_ms":
                round(
                    maximum,
                    2
                ),

            "p90_ms":
                round(
                    p90,
                    2
                ),

            "p95_ms":
                round(
                    p95,
                    2
                ),

            "p99_ms":
                round(
                    p99,
                    2
                ),

            "http_request_rate":
                round(
                    overall_http_request_rate,
                    2
                ),

            "business_tps":
                round(
                    overall_business_tps,
                    2
                ),

            # Backward-compatible field
            "tps":
                round(
                    overall_business_tps,
                    2
                ),

            "error_rate_percent":
                round(
                    error_rate,
                    2
                )
        },


        # --------------------------------
        # Throughput analysis
        # --------------------------------

        "throughput_analysis": {

            "business_transaction":
                business_transaction_label,

            "http_requests_per_business_transaction":
                WORKLOAD[
                    "http_requests_per_business_transaction"
                ],

            "overall_http_request_rate":
                round(
                    overall_http_request_rate,
                    2
                ),

            "overall_business_tps":
                round(
                    overall_business_tps,
                    2
                ),

            "steady_state_start_seconds":
                WORKLOAD[
                    "steady_state_start_seconds"
                ],

            "steady_state_window_seconds":
                round(
                    steady_state_window_seconds,
                    2
                ),

            "steady_state_business_transactions":
                steady_state_business_transactions,

            "steady_state_business_tps":
                round(
                    steady_state_business_tps,
                    2
                ),

            "steady_state_http_request_rate":
                round(
                    steady_state_http_request_rate,
                    2
                )
        },


        # --------------------------------
        # Transaction Summary
        # --------------------------------

        "transaction_summary":
            transaction_summary,


        # --------------------------------
        # Failure Analysis
        # --------------------------------

        "failure_analysis": {

            "by_sampler":
                transaction_summary,

            "by_response_code":
                response_code_stats
        },


        # --------------------------------
        # SLA
        # --------------------------------

        "sla": {

            "required_p95_ms":
                SLA["p95_ms"],

            "required_tps":
                SLA["tps"],

            "required_error_rate_percent":
                SLA[
                    "error_rate_percent"
                ],

            "tps_measurement":
                "steady_state_business_tps",

            "p95_status":
                "PASS"
                if p95_pass
                else "FAIL",

            "tps_status":
                "PASS"
                if tps_pass
                else "FAIL",

            "error_rate_status":
                "PASS"
                if error_pass
                else "FAIL",

            "overall_status":
                "PASS"
                if overall_pass
                else "FAIL"
        }
    }

    return metrics


# ---------------------------------------
# Main
# ---------------------------------------

def main():

    print("====================================")
    print(" AI Performance JTL Analyzer")
    print("====================================")

    print(
        f"Reading JTL: {JTL_FILE}"
    )

    rows = read_jtl()

    print(
        f"Records found: {len(rows)}"
    )

    metrics = analyze(rows)


    # -----------------------------------
    # Save JSON
    # -----------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metrics,
            file,
            indent=4
        )


    # -----------------------------------
    # Performance Analysis
    # -----------------------------------

    print()

    print("Performance Analysis")

    print("------------------------------------")


    print(
        f"Total Requests      : "
        f"{metrics['test_summary']['total_requests']}"
    )

    print(
        f"Successful Requests : "
        f"{metrics['test_summary']['successful_requests']}"
    )

    print(
        f"Failed Requests     : "
        f"{metrics['test_summary']['failed_requests']}"
    )

    print(
        f"Average Response    : "
        f"{metrics['performance_metrics']['average_response_time_ms']} ms"
    )

    print(
        f"P95                 : "
        f"{metrics['performance_metrics']['p95_ms']} ms"
    )

    print(
        f"P99                 : "
        f"{metrics['performance_metrics']['p99_ms']} ms"
    )

    print(
        f"HTTP Request Rate   : "
        f"{metrics['performance_metrics']['http_request_rate']} req/sec"
    )

    print(
        f"Business TPS        : "
        f"{metrics['performance_metrics']['business_tps']}"
    )

    print(
        f"Steady-State TPS    : "
        f"{metrics['throughput_analysis']['steady_state_business_tps']}"
    )

    print(
        f"Steady-State HTTP   : "
        f"{metrics['throughput_analysis']['steady_state_http_request_rate']} req/sec"
    )

    print(
        f"Error Rate          : "
        f"{metrics['performance_metrics']['error_rate_percent']}%"
    )


    # -----------------------------------
    # Transaction Summary
    # -----------------------------------

    print()

    print("Transaction Summary")

    print("------------------------------------")

    print(
        f"{'Transaction':<22}"
        f"{'Total':>8}"
        f"{'Success':>10}"
        f"{'Failed':>9}"
        f"{'Error %':>10}"
    )

    print("-" * 59)


    for transaction, stats in (
        metrics[
            "transaction_summary"
        ].items()
    ):

        print(
            f"{transaction:<22}"
            f"{stats['total']:>8}"
            f"{stats['successful']:>10}"
            f"{stats['failed']:>9}"
            f"{stats['error_rate_percent']:>10.2f}"
        )


    print("-" * 59)


    print(
        f"{'TOTAL':<22}"
        f"{metrics['test_summary']['total_requests']:>8}"
        f"{metrics['test_summary']['successful_requests']:>10}"
        f"{metrics['test_summary']['failed_requests']:>9}"
        f"{metrics['performance_metrics']['error_rate_percent']:>10.2f}"
    )


    # -----------------------------------
    # Throughput Analysis
    # -----------------------------------

    print()

    print("Throughput Analysis")

    print("------------------------------------")


    print(
        f"Business Transaction : "
        f"{metrics['throughput_analysis']['business_transaction']}"
    )

    print(
        f"Overall HTTP Rate    : "
        f"{metrics['throughput_analysis']['overall_http_request_rate']} req/sec"
    )

    print(
        f"Overall Business TPS : "
        f"{metrics['throughput_analysis']['overall_business_tps']}"
    )

    print(
        f"Steady-State Window  : "
        f"{metrics['throughput_analysis']['steady_state_window_seconds']} sec"
    )

    print(
        f"Steady-State Txns    : "
        f"{metrics['throughput_analysis']['steady_state_business_transactions']}"
    )

    print(
        f"Steady-State TPS     : "
        f"{metrics['throughput_analysis']['steady_state_business_tps']}"
    )

    print(
        f"Steady-State HTTP    : "
        f"{metrics['throughput_analysis']['steady_state_http_request_rate']} req/sec"
    )


    # -----------------------------------
    # SLA
    # -----------------------------------

    print()

    print(
        f"SLA Status          : "
        f"{metrics['sla']['overall_status']}"
    )

    print(
        f"SLA TPS Measurement : "
        f"{metrics['sla']['tps_measurement']}"
    )

    print()

    print(
        f"Metrics saved to: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()