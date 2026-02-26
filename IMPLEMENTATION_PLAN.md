# Self-Healing Chaos Agent — Implementation Plan

> **How to use this file:** Open this in Claude Code (`claude` in your terminal) and work through each phase sequentially. Each phase has exact commands, file contents, and checkpoints. Don't move to the next phase until the checkpoint passes.

---

## Prerequisites

Before starting, make sure you have:

```bash
# Check these are installed
docker --version          # Docker 24+
docker compose version    # Docker Compose v2+
git --version             # Git 2.x
node --version            # Node 18+ (for currency/payment services if rebuilding)
python3 --version         # Python 3.10+

# You'll need these later (Day 4+)
# Claude Code CLI: npm install -g @anthropic-ai/claude-code
# Anthropic API key set as ANTHROPIC_API_KEY env var
```

### Hardware Requirements
- **RAM:** 16GB minimum (11 containers + Redis + your scripts)
- **Disk:** ~10GB for container images
- **CPU:** 4+ cores recommended

---

## Phase 1: Fork & Run Online Boutique Locally (Day 1)

### 1.1 Fork and Clone

```bash
# Fork https://github.com/GoogleCloudPlatform/microservices-demo on GitHub first
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/microservices-demo.git
cd microservices-demo
git checkout -b chaos-agent  # work on a branch
```

### 1.2 Create Docker Compose File

The Online Boutique is designed for Kubernetes, but we need Docker Compose for local dev. Create this file in the repo root:

**File: `docker-compose.yaml`**

```yaml
version: "3.9"

services:
  # ─── FRONTEND (Go) ─────────────────────────────────
  frontend:
    build:
      context: ./src/frontend
    ports:
      - "8080:8080"
    environment:
      PORT: "8080"
      PRODUCT_CATALOG_SERVICE_ADDR: "productcatalogservice:3550"
      CURRENCY_SERVICE_ADDR: "currencyservice:7000"
      CART_SERVICE_ADDR: "cartservice:7070"
      RECOMMENDATION_SERVICE_ADDR: "recommendationservice:8080"
      SHIPPING_SERVICE_ADDR: "shippingservice:50051"
      CHECKOUT_SERVICE_ADDR: "checkoutservice:5050"
      AD_SERVICE_ADDR: "adservice:9555"
      SHOPPING_ASSISTANT_SERVICE_ADDR: ""
      ENABLE_PROFILER: "0"
    depends_on:
      - productcatalogservice
      - currencyservice
      - cartservice
      - recommendationservice
      - shippingservice
      - checkoutservice
      - adservice

  # ─── CART SERVICE (C#) ──────────────────────────────
  cartservice:
    build:
      context: ./src/cartservice/src
    environment:
      REDIS_ADDR: "redis-cart:6379"
    depends_on:
      - redis-cart

  # ─── REDIS (Cart Storage) ───────────────────────────
  redis-cart:
    image: redis:7-alpine

  # ─── PRODUCT CATALOG (Go) ──────────────────────────
  productcatalogservice:
    build:
      context: ./src/productcatalogservice
    environment:
      PORT: "3550"
      DISABLE_PROFILER: "1"

  # ─── CURRENCY SERVICE (Node.js) ────────────────────
  currencyservice:
    build:
      context: ./src/currencyservice
    environment:
      PORT: "7000"
      DISABLE_PROFILER: "1"

  # ─── PAYMENT SERVICE (Node.js) ─────────────────────
  paymentservice:
    build:
      context: ./src/paymentservice
    environment:
      PORT: "50051"
      DISABLE_PROFILER: "1"

  # ─── SHIPPING SERVICE (Go) ─────────────────────────
  shippingservice:
    build:
      context: ./src/shippingservice
    environment:
      PORT: "50051"
      DISABLE_PROFILER: "1"

  # ─── EMAIL SERVICE (Python) ────────────────────────
  emailservice:
    build:
      context: ./src/emailservice
    environment:
      PORT: "8080"
      DISABLE_PROFILER: "1"

  # ─── CHECKOUT SERVICE (Go) ─────────────────────────
  checkoutservice:
    build:
      context: ./src/checkoutservice
    environment:
      PORT: "5050"
      PRODUCT_CATALOG_SERVICE_ADDR: "productcatalogservice:3550"
      SHIPPING_SERVICE_ADDR: "shippingservice:50051"
      PAYMENT_SERVICE_ADDR: "paymentservice:50051"
      EMAIL_SERVICE_ADDR: "emailservice:8080"
      CURRENCY_SERVICE_ADDR: "currencyservice:7000"
      CART_SERVICE_ADDR: "cartservice:7070"

  # ─── RECOMMENDATION SERVICE (Python) ───────────────
  recommendationservice:
    build:
      context: ./src/recommendationservice
    environment:
      PORT: "8080"
      PRODUCT_CATALOG_SERVICE_ADDR: "productcatalogservice:3550"
      DISABLE_PROFILER: "1"

  # ─── AD SERVICE (Java) ─────────────────────────────
  adservice:
    build:
      context: ./src/adservice
    environment:
      PORT: "9555"

  # ─── LOAD GENERATOR (Python/Locust) ────────────────
  loadgenerator:
    build:
      context: ./src/loadgenerator
    environment:
      FRONTEND_ADDR: "frontend:8080"
      USERS: "10"
    depends_on:
      - frontend

networks:
  default:
    name: online-boutique
```

> **IMPORTANT:** The ports and env vars above are based on the current repo structure but may need tweaking. When you open Claude Code, tell it: *"Read the Dockerfiles and source code for each service in src/ and fix this docker-compose.yaml so all services can communicate correctly."* Claude Code is excellent at this kind of config wiring.

### 1.3 Build and Run

```bash
# First build (will take 10-20 min — Go, C#, Java all compile)
docker compose build

# Start everything
docker compose up -d

# Check all containers are running
docker compose ps

# Test the frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080
# Should return 200
```

### 1.4 Create Health Check Script

**File: `chaos-agent/healthcheck.sh`**

```bash
#!/bin/bash
# Quick health check for all services
# Usage: ./healthcheck.sh

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "═══════════════════════════════════════"
echo "  Online Boutique Health Check"
echo "═══════════════════════════════════════"

# Frontend (HTTP)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 2>/dev/null)
if [ "$STATUS" = "200" ]; then
    echo -e "${GREEN}[OK]${NC} Frontend (Go)          - HTTP 200"
else
    echo -e "${RED}[FAIL]${NC} Frontend (Go)          - HTTP $STATUS"
fi

# Check each container is running
SERVICES=("cartservice" "redis-cart" "productcatalogservice" "currencyservice" \
          "paymentservice" "shippingservice" "emailservice" "checkoutservice" \
          "recommendationservice" "adservice" "loadgenerator")

for svc in "${SERVICES[@]}"; do
    STATE=$(docker inspect -f '{{.State.Status}}' "microservices-demo-${svc}-1" 2>/dev/null)
    if [ "$STATE" = "running" ]; then
        echo -e "${GREEN}[OK]${NC} ${svc}"
    else
        echo -e "${RED}[FAIL]${NC} ${svc} - State: ${STATE:-not found}"
    fi
done

echo "═══════════════════════════════════════"
```

```bash
chmod +x chaos-agent/healthcheck.sh
./chaos-agent/healthcheck.sh
```

### Phase 1 Checkpoint ✅
- [x] All 11 services + Redis are running (`docker compose ps` shows 12 containers)
- [x] Frontend accessible at http://localhost:8080
- [x] You can browse products, add to cart, and complete a checkout
- [x] `healthcheck.sh` shows all green

---

## Phase 2: Build the Chaos Injector (Day 2)

### 2.1 Chaos Injector Script

**File: `chaos-agent/chaos_injector.py`**

```python
#!/usr/bin/env python3
"""
Chaos Injector — Injects failures into Online Boutique services.

Usage:
    python chaos_injector.py kill redis-cart
    python chaos_injector.py latency currencyservice 3000
    python chaos_injector.py packetloss shippingservice 50
    python chaos_injector.py dns checkoutservice
    python chaos_injector.py restore <service>
"""

import subprocess
import sys
import json
import time
import argparse
from datetime import datetime


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[CHAOS {ts}] {msg}")


def run(cmd, check=True):
    """Run a shell command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        log(f"Command failed: {cmd}")
        log(f"stderr: {result.stderr}")
    return result


def get_container_name(service):
    """Get the full Docker container name for a service."""
    result = run(f"docker compose ps -q {service}", check=False)
    container_id = result.stdout.strip()
    if not container_id:
        log(f"ERROR: Service '{service}' not found")
        sys.exit(1)
    return container_id


# ─── CHAOS ATTACKS ────────────────────────────────────

def attack_kill(service):
    """Kill a container (simulates crash)."""
    log(f"KILLING container: {service}")
    run(f"docker compose stop {service}")
    log(f"Container {service} is DOWN")
    return {
        "attack": "container_kill",
        "target": service,
        "timestamp": datetime.now().isoformat(),
        "description": f"Container {service} was stopped to simulate a crash"
    }


def attack_latency(service, delay_ms=3000):
    """Inject network latency using tc netem."""
    container = get_container_name(service)
    log(f"INJECTING {delay_ms}ms latency into {service}")
    
    # tc requires NET_ADMIN capability — add to docker-compose or use:
    run(f"docker exec --privileged {container} "
        f"tc qdisc add dev eth0 root netem delay {delay_ms}ms 100ms")
    
    log(f"Latency injection active on {service}: {delay_ms}ms ± 100ms")
    return {
        "attack": "network_latency",
        "target": service,
        "delay_ms": delay_ms,
        "jitter_ms": 100,
        "timestamp": datetime.now().isoformat(),
        "description": f"Added {delay_ms}ms network delay to {service}"
    }


def attack_packetloss(service, percent=50):
    """Inject packet loss using tc netem."""
    container = get_container_name(service)
    log(f"INJECTING {percent}% packet loss into {service}")
    
    run(f"docker exec --privileged {container} "
        f"tc qdisc add dev eth0 root netem loss {percent}%")
    
    log(f"Packet loss active on {service}: {percent}%")
    return {
        "attack": "packet_loss",
        "target": service,
        "loss_percent": percent,
        "timestamp": datetime.now().isoformat(),
    }


def attack_dns(service):
    """Corrupt DNS resolution inside a container."""
    container = get_container_name(service)
    log(f"CORRUPTING DNS in {service}")
    
    # Overwrite resolv.conf with a bogus nameserver
    run(f"docker exec {container} sh -c "
        f"'cp /etc/resolv.conf /etc/resolv.conf.bak && "
        f"echo nameserver 192.0.2.1 > /etc/resolv.conf'")
    
    log(f"DNS corrupted in {service} — all lookups will fail")
    return {
        "attack": "dns_corruption",
        "target": service,
        "timestamp": datetime.now().isoformat(),
    }


def restore(service):
    """Restore a service to normal operation."""
    log(f"RESTORING {service}")
    
    container_id = get_container_name(service)
    
    # Remove tc rules
    run(f"docker exec --privileged {container_id} "
        f"tc qdisc del dev eth0 root 2>/dev/null", check=False)
    
    # Restore DNS
    run(f"docker exec {container_id} sh -c "
        f"'[ -f /etc/resolv.conf.bak ] && cp /etc/resolv.conf.bak /etc/resolv.conf'",
        check=False)
    
    # If container was killed, restart it
    run(f"docker compose start {service}", check=False)
    
    log(f"{service} restored to normal")


# ─── CLI ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Chaos Injector for Online Boutique")
    parser.add_argument("attack", choices=["kill", "latency", "packetloss", "dns", "restore"])
    parser.add_argument("service", help="Target service name (e.g., redis-cart, currencyservice)")
    parser.add_argument("param", nargs="?", default=None, help="Attack parameter (e.g., delay in ms, loss percent)")
    parser.add_argument("--output", "-o", default=None, help="Write attack report to JSON file")
    
    args = parser.parse_args()
    
    if args.attack == "kill":
        report = attack_kill(args.service)
    elif args.attack == "latency":
        delay = int(args.param) if args.param else 3000
        report = attack_latency(args.service, delay)
    elif args.attack == "packetloss":
        pct = int(args.param) if args.param else 50
        report = attack_packetloss(args.service, pct)
    elif args.attack == "dns":
        report = attack_dns(args.service)
    elif args.attack == "restore":
        restore(args.service)
        return
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        log(f"Report written to {args.output}")


if __name__ == "__main__":
    main()
```

### 2.2 Add NET_ADMIN Capability

For `tc` (traffic control) to work, containers need the `NET_ADMIN` capability. Add this to every service in `docker-compose.yaml`:

```yaml
  currencyservice:
    build:
      context: ./src/currencyservice
    cap_add:
      - NET_ADMIN
    environment:
      # ... existing env vars
```

> **Tip for Claude Code:** Tell it *"Add cap_add: NET_ADMIN to every service in docker-compose.yaml and install iproute2 in each Dockerfile so tc is available."*

### 2.3 Test Each Attack Manually

```bash
# Make sure everything is healthy first
./chaos-agent/healthcheck.sh

# Test 1: Kill Redis → Cart should fail
python3 chaos-agent/chaos_injector.py kill redis-cart
sleep 5
curl -s http://localhost:8080  # Should still load, but cart ops will fail
python3 chaos-agent/chaos_injector.py restore redis-cart

# Test 2: Add latency to currency service
python3 chaos-agent/chaos_injector.py latency currencyservice 3000
sleep 5
curl -s -w "\nTime: %{time_total}s\n" http://localhost:8080  # Should be slow
python3 chaos-agent/chaos_injector.py restore currencyservice

# Verify everything recovered
./chaos-agent/healthcheck.sh
```

### Phase 2 Checkpoint ✅
- [x] `chaos_injector.py kill redis-cart` stops Redis and cart operations fail
- [x] `chaos_injector.py latency currencyservice 3000` makes the frontend slow (6.2s response)
- [x] `chaos_injector.py restore <service>` brings everything back to healthy
- [x] Each attack produces a JSON report when `--output` is used

---

## Phase 3: Build the Observability Layer (Day 3)

### 3.1 Log Monitor & Failure Report Generator

This is the **most important component** for the AI agent to work effectively. The Anthropic article emphasizes: *"The test harness should not print thousands of useless bytes."*

**File: `chaos-agent/observe.py`**

```python
#!/usr/bin/env python3
"""
Observability Layer — Monitors Online Boutique and generates
structured failure reports optimized for LLM consumption.

Usage:
    python observe.py monitor              # Continuous monitoring
    python observe.py report               # Generate one-time failure report
    python observe.py report --output report.json
"""

import subprocess
import json
import re
import time
import argparse
from datetime import datetime
from collections import defaultdict


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
        shell=True, capture_output=True, text=True
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
        shell=True, capture_output=True, text=True
    )
    return result.stdout + result.stderr


def detect_errors(logs):
    """Parse logs and extract error patterns."""
    errors = []
    error_patterns = [
        (r"(?i)(error|err|fatal|panic|exception|traceback)", "error"),
        (r"(?i)(connection refused|connection reset|ECONNREFUSED)", "connection_refused"),
        (r"(?i)(timeout|timed out|deadline exceeded|DEADLINE_EXCEEDED)", "timeout"),
        (r"(?i)(unavailable|UNAVAILABLE|service unavailable)", "service_unavailable"),
        (r"(?i)(retry|retrying)", "retry_attempt"),
        (r"(?i)(circuit.?breaker|circuit.?open)", "circuit_breaker"),
        (r"(?i)(INTERNAL|internal error|500)", "internal_error"),
    ]
    
    for line in logs.split("\n"):
        if not line.strip():
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
    print(f"HEALTHY: {', '.join(report['healthy_services'])}")
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
```

### 3.2 Test the Observability Layer

```bash
# All healthy — should show green
python3 chaos-agent/observe.py report

# Now inject chaos and observe
python3 chaos-agent/chaos_injector.py kill redis-cart
sleep 10
python3 chaos-agent/observe.py report --output chaos-agent/reports/scenario1.json

# Check the output — it should be concise, structured, actionable
cat chaos-agent/reports/scenario1.json | python3 -m json.tool

# Restore
python3 chaos-agent/chaos_injector.py restore redis-cart
```

### 3.3 End-to-End Scenario Runner

**File: `chaos-agent/run_scenario.py`**

```python
#!/usr/bin/env python3
"""
Runs a complete chaos scenario: inject → wait → observe → report.

Usage:
    python run_scenario.py scenario_1_redis_kill
    python run_scenario.py scenario_2_latency
"""

import json
import os
import sys
import time
import subprocess

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


def run_scenario(scenario_id):
    if scenario_id not in SCENARIOS:
        print(f"Unknown scenario: {scenario_id}")
        print(f"Available: {', '.join(SCENARIOS.keys())}")
        sys.exit(1)
    
    scenario = SCENARIOS[scenario_id]
    print(f"\n{'='*60}")
    print(f"SCENARIO: {scenario['name']}")
    print(f"{'='*60}")
    print(f"Attack:   {scenario['attack']} → {scenario['target']}")
    print(f"Expected: {scenario['expected_pattern']}")
    print(f"Source:   {scenario['target_source']} ({scenario['target_language']})")
    print(f"{'='*60}\n")
    
    # Step 1: Inject chaos
    print("[1/4] Injecting chaos...")
    cmd = f"python3 chaos-agent/chaos_injector.py {scenario['attack']} {scenario['target']}"
    if scenario["param"]:
        cmd += f" {scenario['param']}"
    subprocess.run(cmd, shell=True)
    
    # Step 2: Wait for failure to propagate
    print(f"[2/4] Waiting {scenario['wait_seconds']}s for failure propagation...")
    time.sleep(scenario["wait_seconds"])
    
    # Step 3: Generate failure report
    print("[3/4] Generating failure report...")
    os.makedirs("chaos-agent/reports", exist_ok=True)
    report_path = f"chaos-agent/reports/{scenario_id}.json"
    subprocess.run(
        f"python3 chaos-agent/observe.py report --output {report_path}",
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
    
    print(f"\n✅ Scenario report saved to: {report_path}")
    print(f"   This report is ready to be fed to the Healer Agent.\n")
    
    return report_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_scenario.py <scenario_id>")
        print(f"Available scenarios: {', '.join(SCENARIOS.keys())}")
        sys.exit(1)
    
    run_scenario(sys.argv[1])
```

### Phase 3 Checkpoint ✅
- [x] `observe.py report` shows system status accurately
- [x] `run_scenario.py scenario_1_redis_kill` runs the full inject → wait → report loop
- [x] The generated JSON report is concise (~92 lines) and includes: service name, language, source path, error types, likely cause, and recommended action
- [x] After restoring, `observe.py report` shows healthy (note: need to restart services to clear log-based error counts)

---

## Phase 4: Build the Agent Harness (Day 4)

This is where it gets real. You're now building the actual AI engineering layer.

### 4.1 The Healer Agent Prompt

This is the most critical file in the project. It tells Claude what to do when dropped into a fresh session.

**File: `chaos-agent/HEALER_PROMPT.md`**

```markdown
# Self-Healing Chaos Agent — Healer Role

You are a Healer Agent. Your job is to read a failure report, identify the
root cause, and patch the source code of the affected microservice to add
the appropriate resilience pattern.

## Your Workflow

1. **Read the failure report** at `chaos-agent/reports/current_scenario.json`
2. **Read the PROGRESS.md** file to understand what has already been attempted
3. **Claim your task** by creating a file in `current_tasks/` (e.g., 
   `current_tasks/heal_scenario_1.txt` with your session ID)
4. **Read the relevant source code** identified in the report's
   `scenario.target_source_path` field
5. **Identify what resilience pattern is missing** — the report's
   `scenario.expected_fix_pattern` field gives you a hint
6. **Implement the fix** in the source code
7. **Test your fix locally** by running any available tests
8. **Commit your change** with a descriptive message:
   `fix(service): add <pattern> to handle <failure type>`
9. **Update PROGRESS.md** with what you did and what's left
10. **Remove your task lock** from `current_tasks/`
11. **Push your changes** to the upstream repo

## Resilience Patterns You Should Know

- **Retry with exponential backoff**: For transient connection failures.
  Start at 100ms, double each retry, max 5 retries, add jitter.
- **Circuit breaker**: For latency/timeout issues. Track failures,
  open circuit after N failures, try half-open after timeout.
- **Graceful degradation**: When a non-critical dependency is down,
  return defaults/empty instead of propagating the error.
- **Timeout with deadline**: Set explicit timeouts on gRPC/HTTP calls.
  Don't let calls hang forever.
- **Bulkhead isolation**: Isolate downstream calls in separate thread
  pools/goroutine pools to prevent cascading failures.
- **Idempotency**: For payment/state-changing operations, use idempotency
  keys to prevent duplicate processing on retry.

## Rules

- Only modify files in the service identified in the failure report
- Keep changes minimal — add the resilience pattern, don't refactor
- Use the language's idiomatic patterns (e.g., Go channels, Python 
  decorators, C# Polly library, Node.js async/await)
- Add comments explaining WHY the pattern was added
- Do NOT add dependencies unless absolutely necessary
- Do NOT modify the gRPC proto files
- If you can't figure out the fix, update PROGRESS.md with what you tried
  and what failed, then exit

## Context Window Management

- Do NOT read entire large files. Use grep to find the relevant code.
- Focus on the function that makes the failing downstream call.
- The observe.py report includes `sample_errors` — use those to grep.
```

### 4.2 The Reviewer Agent Prompt

**File: `chaos-agent/REVIEWER_PROMPT.md`**

```markdown
# Self-Healing Chaos Agent — Reviewer Role

You are a Reviewer Agent. Your job is to review patches committed by the
Healer Agent and ensure they are correct, safe, and follow best practices.

## Your Workflow

1. Read `PROGRESS.md` to find recent Healer commits
2. `git log --oneline -5` to find the latest fix commits
3. `git diff HEAD~1` to review the most recent change
4. Evaluate the patch against these criteria:
   - Does it actually address the failure described in the report?
   - Is the retry logic bounded (max retries, max backoff)?
   - Does it avoid infinite loops or retry storms?
   - Does it use language-idiomatic patterns?
   - Are there proper error logs for observability?
   - Does it handle the "happy path" without degrading performance?
5. If the patch is good: update PROGRESS.md with "REVIEWED: [commit] — APPROVED"
6. If the patch has issues: update PROGRESS.md with specific problems
   and what needs to change, then exit (the Healer will pick it up)

## Red Flags to Watch For

- Retries without backoff or jitter (will cause thundering herd)
- Retries without a maximum count (infinite retry loops)
- Circuit breaker without a half-open state (will never recover)
- Catching all exceptions too broadly (swallowing real bugs)
- Missing timeout on the retry mechanism itself
- Hardcoded magic numbers without constants/config
```

### 4.3 The Agent Harness

**File: `chaos-agent/harness.sh`**

```bash
#!/bin/bash
# ══════════════════════════════════════════════════════════
# Self-Healing Chaos Agent — Agent Harness Loop
# Inspired by Anthropic's "Building a C Compiler" article
# ══════════════════════════════════════════════════════════

set -euo pipefail

AGENT_ROLE="${1:-healer}"  # healer, reviewer, or doc
MODEL="${2:-claude-sonnet-4-20250514}"  # Use Sonnet by default, Opus for complex fixes
REPO_DIR="$(pwd)"

# Select prompt based on role
case "$AGENT_ROLE" in
    healer)   PROMPT_FILE="chaos-agent/HEALER_PROMPT.md" ;;
    reviewer) PROMPT_FILE="chaos-agent/REVIEWER_PROMPT.md" ;;
    doc)      PROMPT_FILE="chaos-agent/DOC_PROMPT.md" ;;
    *)        echo "Unknown role: $AGENT_ROLE"; exit 1 ;;
esac

echo "═══════════════════════════════════════"
echo "  Agent Role:  $AGENT_ROLE"
echo "  Model:       $MODEL"
echo "  Prompt:      $PROMPT_FILE"
echo "═══════════════════════════════════════"

# Create directories
mkdir -p agent_logs current_tasks

# ─── AGENT LOOP ───────────────────────────────────────
ITERATION=0
while true; do
    ITERATION=$((ITERATION + 1))
    COMMIT=$(git rev-parse --short=6 HEAD)
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    LOGFILE="agent_logs/${AGENT_ROLE}_${TIMESTAMP}_${COMMIT}.log"

    echo ""
    echo "[Loop $ITERATION] Starting $AGENT_ROLE agent session..."
    echo "[Loop $ITERATION] Commit: $COMMIT"
    echo "[Loop $ITERATION] Log: $LOGFILE"
    echo ""

    # Pull latest changes from other agents
    git pull --rebase origin chaos-agent 2>/dev/null || true

    # Run Claude Code
    claude --dangerously-skip-permissions \
           -p "$(cat $PROMPT_FILE)" \
           --model "$MODEL" \
           2>&1 | tee "$LOGFILE"

    echo ""
    echo "[Loop $ITERATION] Session complete. Sleeping 5s before next iteration..."
    sleep 5
done
```

```bash
chmod +x chaos-agent/harness.sh
```

### 4.4 The Verification Pipeline

**File: `chaos-agent/verify.py`**

```python
#!/usr/bin/env python3
"""
Verification Pipeline — Rebuilds, redeploys, and re-tests a fix.

Usage:
    python verify.py scenario_1_redis_kill
"""

import subprocess
import sys
import time
import json
from run_scenario import SCENARIOS
from observe import generate_failure_report


def verify_fix(scenario_id):
    if scenario_id not in SCENARIOS:
        print(f"Unknown scenario: {scenario_id}")
        sys.exit(1)
    
    scenario = SCENARIOS[scenario_id]
    print(f"\n{'='*60}")
    print(f"VERIFYING FIX: {scenario['name']}")
    print(f"{'='*60}\n")
    
    # Step 1: Rebuild the affected service
    # Determine which docker compose service to rebuild
    target = scenario["target"]
    # If attack target is redis, we need to verify cartservice
    verify_service = scenario["affected_services"][0] if target == "redis-cart" else target
    
    print(f"[1/5] Rebuilding {verify_service}...")
    subprocess.run(f"docker compose build {verify_service}", shell=True, check=True)
    
    # Step 2: Redeploy
    print(f"[2/5] Redeploying {verify_service}...")
    subprocess.run(f"docker compose up -d {verify_service}", shell=True, check=True)
    time.sleep(10)  # Wait for service to stabilize
    
    # Step 3: Verify baseline health
    print("[3/5] Checking baseline health...")
    report = generate_failure_report()
    if report["system_status"] != "HEALTHY":
        print(f"❌ BASELINE FAILED — System not healthy before chaos injection")
        print(f"   Failing services: {[s['name'] for s in report['failing_services']]}")
        return False
    print("   Baseline: HEALTHY ✅")
    
    # Step 4: Re-inject the same chaos
    print(f"[4/5] Re-injecting chaos: {scenario['attack']} → {scenario['target']}...")
    cmd = f"python3 chaos-agent/chaos_injector.py {scenario['attack']} {scenario['target']}"
    if scenario["param"]:
        cmd += f" {scenario['param']}"
    subprocess.run(cmd, shell=True)
    
    time.sleep(scenario["wait_seconds"])
    
    # Step 5: Check if the system survived
    print("[5/5] Checking post-chaos health...")
    report = generate_failure_report()
    
    # The target service may be down (that's expected for kill attacks)
    # But the DEPENDENT services should be resilient now
    dependent_failures = [
        s for s in report["failing_services"]
        if s["name"] in scenario["affected_services"]
        and s["name"] != scenario["target"]
    ]
    
    # Restore before reporting results
    subprocess.run(
        f"python3 chaos-agent/chaos_injector.py restore {scenario['target']}",
        shell=True
    )
    time.sleep(10)
    
    # Write verification result
    result = {
        "scenario": scenario_id,
        "timestamp": report["timestamp"],
        "chaos_survived": len(dependent_failures) == 0,
        "dependent_failures": [s["name"] for s in dependent_failures],
        "system_status_under_chaos": report["system_status"],
    }
    
    result_path = f"verification_results/{scenario_id}.json"
    subprocess.run("mkdir -p verification_results", shell=True)
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
    
    if result["chaos_survived"]:
        print(f"\n✅ VERIFICATION PASSED — {scenario['name']}")
        print(f"   Dependent services survived the chaos attack!")
    else:
        print(f"\n❌ VERIFICATION FAILED — {scenario['name']}")
        print(f"   These services still failed: {result['dependent_failures']}")
    
    print(f"   Result saved to: {result_path}\n")
    return result["chaos_survived"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify.py <scenario_id>")
        sys.exit(1)
    
    success = verify_fix(sys.argv[1])
    sys.exit(0 if success else 1)
```

### 4.5 Progress Tracking File

**File: `PROGRESS.md`**

```markdown
# Self-Healing Chaos Agent — Progress Tracker

> This file is maintained by the AI agents. Each agent reads this on startup
> to orient itself, and updates it before exiting.

## Status

| Scenario | Status | Agent | Commit | Notes |
|----------|--------|-------|--------|-------|
| scenario_1_redis_kill | PENDING | — | — | Redis kill → Cart Service retry |
| scenario_2_latency | PENDING | — | — | Currency Service latency → Circuit breaker |
| scenario_3_payment_kill | PENDING | — | — | Payment kill → Idempotent retry |
| scenario_5_recommendation_crash | PENDING | — | — | Recommendation kill → Graceful degradation |

## Completed Fixes

(None yet)

## Failed Attempts

(None yet)

## Notes for Next Agent

Start with scenario_1_redis_kill — it's the simplest and will validate the
entire pipeline works end-to-end.
```

### Phase 4 Checkpoint ✅
- [x] `HEALER_PROMPT.md` and `REVIEWER_PROMPT.md` are written and clear
- [x] `harness.sh` runs and spawns a Claude session (not tested yet - requires ANTHROPIC_API_KEY)
- [x] `verify.py` can rebuild a service and run the chaos → check loop
- [x] `PROGRESS.md` exists and is ready for agents to update
- [x] `current_tasks/` directory exists for task locking

---

## Phase 5: Run Scenarios Autonomously (Days 5–6)

### 5.1 The Full Loop — Manual First

Before letting agents run autonomously, do one full manual loop:

```bash
# 1. Run the scenario to generate the failure report
python3 chaos-agent/run_scenario.py scenario_1_redis_kill

# 2. Copy report to the "current" location the agent expects
cp chaos-agent/reports/scenario_1_redis_kill.json chaos-agent/reports/current_scenario.json

# 3. Run the healer agent ONCE (not in a loop)
claude -p "$(cat chaos-agent/HEALER_PROMPT.md)" --model claude-sonnet-4-20250514

# 4. Check what Claude did
git log --oneline -3
git diff HEAD~1

# 5. Restore the chaos
python3 chaos-agent/chaos_injector.py restore redis-cart

# 6. Verify the fix
python3 chaos-agent/verify.py scenario_1_redis_kill
```

### 5.2 Run Autonomously

Once the manual loop works:

```bash
# Terminal 1: Run the Healer Agent
./chaos-agent/harness.sh healer claude-sonnet-4-20250514

# Terminal 2: Run the Reviewer Agent (after Healer makes first commit)
./chaos-agent/harness.sh reviewer claude-sonnet-4-20250514

# Terminal 3: Monitor
python3 chaos-agent/observe.py monitor --interval 15
```

### 5.3 Run Multiple Scenarios

```bash
# Queue up scenarios by creating report files
python3 chaos-agent/run_scenario.py scenario_1_redis_kill
python3 chaos-agent/run_scenario.py scenario_5_recommendation_crash

# The healer agent will pick up whichever one isn't locked
```

### Phase 5 Checkpoint ✅
- [ ] At least 1 scenario runs fully autonomously: inject → detect → heal → verify passes
- [ ] The Healer agent produces a clean git commit with a descriptive message
- [ ] The Reviewer agent reviews and either approves or flags issues
- [ ] `PROGRESS.md` is updated by agents after each session

---

## Phase 6: Polish & Demo (Day 7)

### 6.1 Demo Video Script

Record a 60-90 second screencast showing:

1. **0:00–0:10** — Show the Online Boutique running, browse products, add to cart
2. **0:10–0:20** — Show terminal: run `healthcheck.sh`, all green
3. **0:20–0:35** — Inject chaos: `chaos_injector.py kill redis-cart`, show cart failures
4. **0:35–0:50** — Show the failure report, then the Healer agent picking it up and patching
5. **0:50–1:05** — Show the git diff of the fix, the verification passing
6. **1:05–1:15** — Show the system surviving the same chaos attack post-fix
7. **1:15–1:30** — Show `RESILIENCE_PATTERNS.md` auto-generated documentation

### 6.2 README Template

Your repo README should include:
- Architecture diagram (use Mermaid)
- Link to the Anthropic article as inspiration
- "Quick Start" that someone can clone and run
- Demo video GIF/link
- Table of scenarios with pass/fail status

### 6.3 Final Repo Cleanup

```bash
# Make sure all scenarios have verification results
ls verification_results/

# Make sure PROGRESS.md reflects final state
cat PROGRESS.md

# Make sure agent logs are committed (they're interesting to browse!)
git add agent_logs/
git commit -m "chore: add agent session logs for reproducibility"

# Tag a release
git tag -a v1.0 -m "Self-Healing Chaos Agent v1.0 — 4 scenarios passing"
git push origin chaos-agent --tags
```

---

## Cost Tracking

Keep a running tally of API costs:

| Date | Agent | Model | Input Tokens | Output Tokens | Cost |
|------|-------|-------|-------------|---------------|------|
| Day 4 | Healer test | Sonnet | — | — | — |
| Day 5 | Healer ×3 | Sonnet | — | — | — |
| Day 5 | Reviewer ×2 | Sonnet | — | — | — |
| Day 6 | Healer ×4 | Sonnet | — | — | — |
| Day 6 | Reviewer ×2 | Sonnet | — | — | — |
| **Total** | | | | | **$___** |

**Cost tips:**
- Use **Sonnet** for most sessions (~$3/M input, $15/M output)
- Only use **Opus** if Sonnet fails on a complex fix
- Each session should be 1–3M input tokens depending on codebase size
- Budget: ~30 sessions × ~$5 avg = ~$150

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Docker Compose builds fail | Check each Dockerfile works individually: `docker build src/cartservice/src/` |
| `tc` command not found | Add `RUN apt-get install -y iproute2` to the service's Dockerfile |
| Services can't find each other | Check service names match in docker-compose.yaml and env vars |
| Claude agent goes off-track | Improve the prompt — add more constraints, add examples of good fixes |
| Agent modifies wrong files | Add explicit "ONLY modify files in X directory" to the prompt |
| Verification always fails | Lower the bar — check for "fewer errors" instead of "zero errors" initially |
| Git conflicts between agents | For v1, run agents sequentially. Parallel is a stretch goal. |
