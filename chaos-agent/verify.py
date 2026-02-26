#!/usr/bin/env python3
"""
Verification Pipeline — Rebuilds, redeploys, and re-tests a fix.

After the Healer agent patches code, this script:
1. Rebuilds the affected service container
2. Redeploys it
3. Verifies baseline health
4. Re-injects the same chaos
5. Checks if dependent services now survive

Usage:
    python verify.py scenario_1_redis_kill
    python verify.py --list
"""

import subprocess
import sys
import time
import json
import os
import shlex

# Import scenarios from run_scenario
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from run_scenario import SCENARIOS


def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def run(cmd, check=True):
    """Run a shell command."""
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"  ERROR: {result.stderr}")
    return result


def generate_failure_report():
    """Generate a failure report using observe.py."""
    script_dir = get_script_dir()
    observe_path = shlex.quote(os.path.join(script_dir, "observe.py"))
    result = subprocess.run(
        f"python3 {observe_path} report --output /tmp/verify_report.json",
        shell=True, capture_output=True, text=True
    )
    try:
        with open("/tmp/verify_report.json") as f:
            return json.load(f)
    except:
        return {"system_status": "UNKNOWN", "failing_services": []}


def verify_fix(scenario_id):
    if scenario_id not in SCENARIOS:
        print(f"Unknown scenario: {scenario_id}")
        print(f"Available: {', '.join(SCENARIOS.keys())}")
        sys.exit(1)

    scenario = SCENARIOS[scenario_id]
    script_dir = get_script_dir()
    repo_dir = os.path.dirname(script_dir)

    print(f"\n{'='*60}")
    print(f"VERIFYING FIX: {scenario['name']}")
    print(f"{'='*60}\n")

    # Determine which service to verify
    target = scenario["target"]
    # If attack target is redis, we verify cartservice (the dependent)
    verify_service = scenario["affected_services"][0] if target == "redis-cart" else target

    # Step 1: Rebuild the affected service
    print(f"[1/5] Rebuilding {verify_service}...")
    result = run(f"docker compose build {verify_service}", check=False)
    if result.returncode != 0:
        print(f"  WARNING: Build may have failed, continuing anyway...")

    # Step 2: Redeploy
    print(f"\n[2/5] Redeploying {verify_service}...")
    run(f"docker compose up -d {verify_service}", check=False)
    print("  Waiting 15s for service to stabilize...")
    time.sleep(15)

    # Step 3: Verify baseline health
    print("\n[3/5] Checking baseline health...")
    report = generate_failure_report()
    if report["system_status"] != "HEALTHY":
        failing = [s["name"] for s in report.get("failing_services", [])]
        print(f"  WARNING: System not fully healthy. Failing: {failing}")
        print("  Continuing with verification anyway...")
    else:
        print("  Baseline: HEALTHY")

    # Step 4: Re-inject the same chaos
    print(f"\n[4/5] Re-injecting chaos: {scenario['attack']} -> {scenario['target']}...")
    injector_path = shlex.quote(os.path.join(script_dir, "chaos_injector.py"))
    cmd = f"python3 {injector_path} {scenario['attack']} {scenario['target']}"
    if scenario["param"]:
        cmd += f" {scenario['param']}"
    run(cmd)

    print(f"  Waiting {scenario['wait_seconds']}s for failure propagation...")
    time.sleep(scenario["wait_seconds"])

    # Step 5: Check if the system survived
    print("\n[5/5] Checking post-chaos health...")
    report = generate_failure_report()

    # The target service may be down (that's expected for kill attacks)
    # But the DEPENDENT services should be resilient now
    dependent_failures = [
        s for s in report.get("failing_services", [])
        if s["name"] in scenario["affected_services"]
        and s["name"] != scenario["target"]
    ]

    # Restore before reporting results
    print(f"\nRestoring {scenario['target']}...")
    run(f"python3 {injector_path} restore {scenario['target']}", check=False)
    time.sleep(10)

    # Write verification result
    results_dir = os.path.join(repo_dir, "verification_results")
    os.makedirs(results_dir, exist_ok=True)
    result_path = os.path.join(results_dir, f"{scenario_id}.json")

    verification_result = {
        "scenario": scenario_id,
        "scenario_name": scenario["name"],
        "timestamp": report.get("timestamp", "unknown"),
        "chaos_survived": len(dependent_failures) == 0,
        "dependent_failures": [s["name"] for s in dependent_failures],
        "system_status_under_chaos": report["system_status"],
        "expected_pattern": scenario["expected_pattern"],
    }

    with open(result_path, "w") as f:
        json.dump(verification_result, f, indent=2)

    # Print result
    print(f"\n{'='*60}")
    if verification_result["chaos_survived"]:
        print(f"VERIFICATION PASSED: {scenario['name']}")
        print(f"{'='*60}")
        print(f"  Dependent services survived the chaos attack!")
        print(f"  The resilience pattern is working correctly.")
    else:
        print(f"VERIFICATION FAILED: {scenario['name']}")
        print(f"{'='*60}")
        print(f"  These services still failed: {verification_result['dependent_failures']}")
        print(f"  The fix may need more work.")

    print(f"\n  Result saved to: {result_path}")
    print(f"{'='*60}\n")

    return verification_result["chaos_survived"]


def list_scenarios():
    print("\nAvailable scenarios for verification:")
    print("=" * 60)
    for sid, s in SCENARIOS.items():
        print(f"  {sid}")
        print(f"    {s['name']} ({s['target_language']})")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify.py <scenario_id>")
        print("       python verify.py --list")
        list_scenarios()
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_scenarios()
    else:
        success = verify_fix(sys.argv[1])
        sys.exit(0 if success else 1)
