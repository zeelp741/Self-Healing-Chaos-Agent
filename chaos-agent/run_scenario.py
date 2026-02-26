#!/usr/bin/env python3
"""
Runs a complete chaos scenario: inject -> wait -> observe -> report.

Usage:
    python run_scenario.py scenario_1_redis_kill
    python run_scenario.py scenario_2_latency
    python run_scenario.py --list
"""

import json
import os
import sys
import time
import subprocess
import shlex

SCENARIOS = {
    "scenario_1_redis_kill": {
        "name": "Redis Cart Kill",
        "description": "Kill Redis to test Cart Service resilience",
        "attack": "kill",
        "target": "redis-cart",
        "param": None,
        "wait_seconds": 15,
        "affected_services": ["cartservice", "checkoutservice", "frontend"],
        "expected_pattern": "retry with exponential backoff + in-memory fallback",
        "target_source": "src/cartservice/src/",
        "target_language": "C#",
    },
    "scenario_2_latency": {
        "name": "Currency Service Latency",
        "description": "Add 3s latency to Currency Service",
        "attack": "latency",
        "target": "currencyservice",
        "param": "3000",
        "wait_seconds": 15,
        "affected_services": ["frontend", "checkoutservice"],
        "expected_pattern": "circuit breaker with timeout and fallback",
        "target_source": "src/currencyservice/",
        "target_language": "Node.js",
    },
    "scenario_3_payment_kill": {
        "name": "Payment Service Kill",
        "description": "Kill Payment Service to test idempotent retry",
        "attack": "kill",
        "target": "paymentservice",
        "param": None,
        "wait_seconds": 15,
        "affected_services": ["checkoutservice"],
        "expected_pattern": "retry with idempotency key",
        "target_source": "src/paymentservice/",
        "target_language": "Node.js",
    },
    "scenario_4_shipping_packetloss": {
        "name": "Shipping Service Packet Loss",
        "description": "50% packet loss on Shipping Service",
        "attack": "packetloss",
        "target": "shippingservice",
        "param": "50",
        "wait_seconds": 20,
        "affected_services": ["checkoutservice", "frontend"],
        "expected_pattern": "retry with backoff and timeout",
        "target_source": "src/shippingservice/",
        "target_language": "Go",
    },
    "scenario_5_recommendation_crash": {
        "name": "Recommendation Service Crash",
        "description": "Kill Recommendation to test graceful degradation",
        "attack": "kill",
        "target": "recommendationservice",
        "param": None,
        "wait_seconds": 15,
        "affected_services": ["frontend"],
        "expected_pattern": "graceful degradation — return empty recommendations instead of 500",
        "target_source": "src/recommendationservice/",
        "target_language": "Python",
    },
}


def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def run_scenario(scenario_id):
    if scenario_id not in SCENARIOS:
        print(f"Unknown scenario: {scenario_id}")
        print(f"Available: {', '.join(SCENARIOS.keys())}")
        sys.exit(1)

    scenario = SCENARIOS[scenario_id]
    script_dir = get_script_dir()

    print(f"\n{'='*60}")
    print(f"SCENARIO: {scenario['name']}")
    print(f"{'='*60}")
    print(f"Attack:   {scenario['attack']} -> {scenario['target']}")
    print(f"Expected: {scenario['expected_pattern']}")
    print(f"Source:   {scenario['target_source']} ({scenario['target_language']})")
    print(f"{'='*60}\n")

    # Step 1: Inject chaos
    print("[1/4] Injecting chaos...")
    injector_path = shlex.quote(os.path.join(script_dir, "chaos_injector.py"))
    cmd = f"python3 {injector_path} {scenario['attack']} {scenario['target']}"
    if scenario["param"]:
        cmd += f" {scenario['param']}"
    subprocess.run(cmd, shell=True)

    # Step 2: Wait for failure to propagate
    print(f"[2/4] Waiting {scenario['wait_seconds']}s for failure propagation...")
    time.sleep(scenario["wait_seconds"])

    # Step 3: Generate failure report
    print("[3/4] Generating failure report...")
    reports_dir = os.path.join(script_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, f"{scenario_id}.json")
    observe_path = shlex.quote(os.path.join(script_dir, "observe.py"))
    report_path_quoted = shlex.quote(report_path)
    subprocess.run(
        f"python3 {observe_path} report --output {report_path_quoted}",
        shell=True
    )

    # Step 4: Enrich report with scenario context
    print("[4/4] Enriching report with scenario context...")
    with open(report_path) as f:
        report = json.load(f)

    report["scenario"] = {
        "id": scenario_id,
        "name": scenario["name"],
        "attack_type": scenario["attack"],
        "target_service": scenario["target"],
        "expected_fix_pattern": scenario["expected_pattern"],
        "target_source_path": scenario["target_source"],
        "target_language": scenario["target_language"],
        "affected_services": scenario["affected_services"],
    }

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Also copy to current_scenario.json for the healer agent
    current_path = os.path.join(reports_dir, "current_scenario.json")
    with open(current_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n{'='*60}")
    print(f"SCENARIO COMPLETE: {scenario['name']}")
    print(f"{'='*60}")
    print(f"Report saved to: {report_path}")
    print(f"Current scenario: {current_path}")
    print(f"\nNext steps:")
    print(f"  1. Review the report: cat {report_path}")
    print(f"  2. Run the healer: ./harness.sh healer")
    print(f"  3. Restore service: python3 chaos_injector.py restore {scenario['target']}")
    print(f"{'='*60}\n")

    return report_path


def list_scenarios():
    print("\nAvailable Chaos Scenarios:")
    print("=" * 70)
    for sid, s in SCENARIOS.items():
        print(f"\n{sid}:")
        print(f"  Name:     {s['name']}")
        print(f"  Attack:   {s['attack']} -> {s['target']}")
        print(f"  Expected: {s['expected_pattern']}")
        print(f"  Language: {s['target_language']}")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_scenario.py <scenario_id>")
        print("       python run_scenario.py --list")
        list_scenarios()
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_scenarios()
    else:
        run_scenario(sys.argv[1])
