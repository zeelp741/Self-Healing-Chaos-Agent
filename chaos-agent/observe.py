#!/usr/bin/env python3
"""
Observability Layer — Monitors Online Boutique and generates
structured failure reports optimized for LLM consumption.

Usage:
    python observe.py report               # Generate one-time failure report
    python observe.py report --output report.json
    python observe.py monitor              # Continuous monitoring
"""

import subprocess
import json
import re
import time
import argparse
import os
from datetime import datetime
from collections import defaultdict


# Path to the microservices-demo repository
REPO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "microservices-demo")


SERVICES = [
    "frontend", "cartservice", "redis-cart", "productcatalogservice",
    "currencyservice", "paymentservice", "shippingservice",
    "emailservice", "checkoutservice", "recommendationservice", "adservice"
]

SERVICE_LANGUAGES = {
    "frontend": "Go",
    "cartservice": "C#",
    "redis-cart": "Redis",
    "productcatalogservice": "Go",
    "currencyservice": "Node.js",
    "paymentservice": "Node.js",
    "shippingservice": "Go",
    "emailservice": "Python",
    "checkoutservice": "Go",
    "recommendationservice": "Python",
    "adservice": "Java",
}

# Map of source code paths for each service
SERVICE_SOURCE_PATHS = {
    "cartservice": "src/cartservice/src/",
    "currencyservice": "src/currencyservice/",
    "paymentservice": "src/paymentservice/",
    "shippingservice": "src/shippingservice/",
    "emailservice": "src/emailservice/",
    "checkoutservice": "src/checkoutservice/",
    "recommendationservice": "src/recommendationservice/",
    "adservice": "src/adservice/",
    "frontend": "src/frontend/",
    "productcatalogservice": "src/productcatalogservice/",
}


def get_container_status(service):
    """Check if a container is running."""
    result = subprocess.run(
        f"docker compose ps --format json {service}",
        shell=True, capture_output=True, text=True, cwd=REPO_DIR
    )
    try:
        data = json.loads(result.stdout)
        if isinstance(data, list):
            data = data[0] if data else {}
        return {
            "running": data.get("State") == "running",
            "status": data.get("State", "unknown"),
            "health": data.get("Health", "unknown"),
        }
    except (json.JSONDecodeError, IndexError):
        return {"running": False, "status": "not_found", "health": "unknown"}


def get_recent_logs(service, lines=50):
    """Get recent container logs."""
    result = subprocess.run(
        f"docker compose logs --tail={lines} --no-log-prefix {service}",
        shell=True, capture_output=True, text=True, cwd=REPO_DIR
    )
    return result.stdout + result.stderr


def detect_errors(logs):
    """Parse logs and extract error patterns."""
    errors = []
    # Error patterns - more specific to reduce false positives
    error_patterns = [
        # Actual error indicators (word boundaries to avoid matching field names)
        (r'"severity"\s*:\s*"error"', "error"),           # JSON severity: error
        (r'"level"\s*:\s*"error"', "error"),              # JSON level: error
        (r'\berror\b.*\b(failed|cannot|unable)\b', "error"),  # "error ... failed/cannot/unable"
        (r'(?i)\b(fatal|panic)\b', "error"),              # Fatal/panic anywhere
        (r'(?i)\bexception\b', "error"),                  # Exception
        (r'(?i)\btraceback\b', "error"),                  # Python traceback
        (r"(?i)(connection refused|connection reset|ECONNREFUSED)", "connection_refused"),
        (r"(?i)(timeout|timed out|deadline exceeded|DEADLINE_EXCEEDED)", "timeout"),
        (r"(?i)(unavailable|UNAVAILABLE|service unavailable)", "service_unavailable"),
        (r"(?i)(circuit.?breaker|circuit.?open)", "circuit_breaker"),
        # HTTP 500 errors - be specific about response status
        (r'"http\.resp\.status"\s*:\s*5\d\d', "internal_error"),  # HTTP 5xx status
        (r'"status"\s*:\s*5\d\d', "internal_error"),              # Generic status 5xx
        (r'status.?code.*5\d\d', "internal_error"),               # Status code 5xx
        (r'(?i)internal server error', "internal_error"),         # Explicit error message
    ]

    # Patterns that indicate resilience is WORKING (not errors)
    resilience_patterns = [
        r"\[RETRY\]",        # Retry attempt log
        r"\[FALLBACK\]",     # Fallback cache log
        r"\[RESILIENCE\]",   # Resilience check log
    ]

    # Patterns that indicate success (should not be flagged)
    success_patterns = [
        r'"http\.resp\.status"\s*:\s*2\d\d',  # HTTP 2xx success
        r'"severity"\s*:\s*"(info|debug)"',   # Info/debug logs
    ]

    for line in logs.split("\n"):
        if not line.strip():
            continue

        # Skip lines that indicate resilience patterns are working
        is_resilience_log = any(re.search(p, line) for p in resilience_patterns)
        if is_resilience_log:
            continue

        # Skip lines that indicate success
        is_success_log = any(re.search(p, line) for p in success_patterns)
        if is_success_log:
            continue

        for pattern, error_type in error_patterns:
            if re.search(pattern, line):
                errors.append({
                    "type": error_type,
                    "line": line.strip()[:200],  # Truncate for LLM context
                })
                break  # Only match first pattern per line

    return errors


def identify_downstream_failures(service, errors):
    """Determine which downstream service is causing failures."""
    downstream_hints = {
        "redis": "redis-cart",
        "cart": "cartservice",
        "product": "productcatalogservice",
        "currency": "currencyservice",
        "payment": "paymentservice",
        "shipping": "shippingservice",
        "email": "emailservice",
        "checkout": "checkoutservice",
        "recommend": "recommendationservice",
        "ad": "adservice",
    }

    affected_downstreams = set()
    for error in errors:
        for hint, downstream in downstream_hints.items():
            if hint in error["line"].lower() and downstream != service:
                affected_downstreams.add(downstream)

    return list(affected_downstreams)


def suggest_likely_cause(service, errors, container_status):
    """Pre-compute a likely root cause to save agent tokens."""
    if not container_status["running"]:
        return f"Container {service} is DOWN (crashed or stopped)"

    error_types = [e["type"] for e in errors]

    if "connection_refused" in error_types:
        return f"{service} cannot connect to a downstream dependency (connection refused)"
    if "timeout" in error_types:
        return f"{service} is experiencing timeouts calling a downstream service (possible network latency)"
    if "service_unavailable" in error_types:
        return f"A service that {service} depends on is unavailable (gRPC UNAVAILABLE status)"
    if "internal_error" in error_types:
        return f"{service} is returning internal errors (unhandled exception or panic)"

    return "No obvious root cause detected from logs"


def generate_failure_report():
    """
    Generate a structured failure report optimized for LLM consumption.

    Design principles (from Anthropic article):
    - At most 10 lines of summary
    - Pre-computed diagnosis
    - File paths for relevant source code
    - No log flooding
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "system_status": "HEALTHY",
        "failing_services": [],
        "healthy_services": [],
        "error_summary": [],
        "recommended_actions": [],
    }

    for service in SERVICES:
        status = get_container_status(service)
        logs = get_recent_logs(service, lines=100)
        errors = detect_errors(logs)

        service_report = {
            "name": service,
            "language": SERVICE_LANGUAGES.get(service, "unknown"),
            "source_path": SERVICE_SOURCE_PATHS.get(service, ""),
            "status": status["status"],
            "running": status["running"],
            "error_count": len(errors),
        }

        if not status["running"] or len(errors) > 5:
            report["system_status"] = "DEGRADED"
            service_report["likely_cause"] = suggest_likely_cause(service, errors, status)
            service_report["affected_downstreams"] = identify_downstream_failures(service, errors)

            # Deduplicate error types for concise reporting
            error_type_counts = defaultdict(int)
            for e in errors:
                error_type_counts[e["type"]] += 1
            service_report["error_types"] = dict(error_type_counts)

            # Include only the 3 most recent unique error lines
            seen = set()
            unique_errors = []
            for e in reversed(errors):
                if e["line"] not in seen and len(unique_errors) < 3:
                    seen.add(e["line"])
                    unique_errors.append(e["line"])
            service_report["sample_errors"] = unique_errors

            report["failing_services"].append(service_report)
        else:
            report["healthy_services"].append(service_report["name"])

    # Generate concise recommended actions
    for svc in report["failing_services"]:
        if "connection_refused" in svc.get("error_types", {}):
            report["recommended_actions"].append(
                f"ACTION: Add retry with exponential backoff in {svc['source_path']} "
                f"for {svc['name']} ({svc['language']}) when connecting to downstream services"
            )
        if "timeout" in svc.get("error_types", {}):
            report["recommended_actions"].append(
                f"ACTION: Add circuit breaker or timeout handling in {svc['source_path']} "
                f"for {svc['name']} ({svc['language']})"
            )
        if not svc["running"]:
            report["recommended_actions"].append(
                f"ACTION: {svc['name']} is DOWN — dependent services should implement "
                f"graceful degradation (return defaults/empty instead of 500)"
            )

    return report


def print_concise_report(report):
    """Print a max-10-line summary for terminal / LLM context."""
    print("=" * 60)
    print(f"SYSTEM STATUS: {report['system_status']}")
    print(f"TIMESTAMP: {report['timestamp']}")
    print(f"HEALTHY: {', '.join(report['healthy_services']) or 'None'}")
    print("-" * 60)

    for svc in report["failing_services"]:
        status = "DOWN" if not svc["running"] else "ERRORS"
        print(f"ERROR | service={svc['name']} | lang={svc['language']} | "
              f"status={status} | errors={svc['error_count']} | "
              f"cause={svc.get('likely_cause', 'unknown')}")

    print("-" * 60)
    for action in report["recommended_actions"]:
        print(action)
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Online Boutique Observability")
    parser.add_argument("mode", choices=["monitor", "report"])
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument("--interval", type=int, default=10, help="Monitor interval in seconds")

    args = parser.parse_args()

    if args.mode == "report":
        report = generate_failure_report()
        print_concise_report(report)
        if args.output:
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\nFull report saved to {args.output}")

    elif args.mode == "monitor":
        print("Starting continuous monitoring (Ctrl+C to stop)...")
        while True:
            report = generate_failure_report()
            if report["system_status"] != "HEALTHY":
                print_concise_report(report)
                if args.output:
                    with open(args.output, "w") as f:
                        json.dump(report, f, indent=2)
            else:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] All systems healthy")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
