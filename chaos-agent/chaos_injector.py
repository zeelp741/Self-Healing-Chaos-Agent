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


def get_container_id(service):
    """Get the Docker container ID for a service."""
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
    container = get_container_id(service)
    log(f"INJECTING {delay_ms}ms latency into {service}")

    # tc requires NET_ADMIN capability
    result = run(f"docker exec --privileged {container} "
                 f"tc qdisc add dev eth0 root netem delay {delay_ms}ms 100ms",
                 check=False)

    if result.returncode != 0:
        # Try replacing existing qdisc
        run(f"docker exec --privileged {container} "
            f"tc qdisc replace dev eth0 root netem delay {delay_ms}ms 100ms",
            check=False)

    log(f"Latency injection active on {service}: {delay_ms}ms +/- 100ms jitter")
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
    container = get_container_id(service)
    log(f"INJECTING {percent}% packet loss into {service}")

    result = run(f"docker exec --privileged {container} "
                 f"tc qdisc add dev eth0 root netem loss {percent}%",
                 check=False)

    if result.returncode != 0:
        run(f"docker exec --privileged {container} "
            f"tc qdisc replace dev eth0 root netem loss {percent}%",
            check=False)

    log(f"Packet loss active on {service}: {percent}%")
    return {
        "attack": "packet_loss",
        "target": service,
        "loss_percent": percent,
        "timestamp": datetime.now().isoformat(),
        "description": f"Added {percent}% packet loss to {service}"
    }


def attack_dns(service):
    """Corrupt DNS resolution inside a container."""
    container = get_container_id(service)
    log(f"CORRUPTING DNS in {service}")

    # Backup and overwrite resolv.conf with a bogus nameserver
    run(f"docker exec {container} sh -c "
        f"'cp /etc/resolv.conf /etc/resolv.conf.bak 2>/dev/null; "
        f"echo nameserver 192.0.2.1 > /etc/resolv.conf'",
        check=False)

    log(f"DNS corrupted in {service} — all DNS lookups will fail")
    return {
        "attack": "dns_corruption",
        "target": service,
        "timestamp": datetime.now().isoformat(),
        "description": f"DNS resolution corrupted in {service}"
    }


def restore(service):
    """Restore a service to normal operation."""
    log(f"RESTORING {service}")

    # Try to get container ID (might not exist if killed)
    result = run(f"docker compose ps -q {service}", check=False)
    container_id = result.stdout.strip()

    if container_id:
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
    return {
        "action": "restore",
        "target": service,
        "timestamp": datetime.now().isoformat(),
    }


# ─── CLI ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Chaos Injector for Online Boutique",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python chaos_injector.py kill redis-cart
    python chaos_injector.py latency currencyservice 3000
    python chaos_injector.py packetloss shippingservice 50
    python chaos_injector.py dns checkoutservice
    python chaos_injector.py restore redis-cart
        """
    )
    parser.add_argument("attack",
                        choices=["kill", "latency", "packetloss", "dns", "restore"],
                        help="Type of chaos to inject")
    parser.add_argument("service",
                        help="Target service name (e.g., redis-cart, currencyservice)")
    parser.add_argument("param", nargs="?", default=None,
                        help="Attack parameter (delay in ms for latency, percent for packetloss)")
    parser.add_argument("--output", "-o", default=None,
                        help="Write attack report to JSON file")

    args = parser.parse_args()

    report = None

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
        report = restore(args.service)

    if args.output and report:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        log(f"Report written to {args.output}")

    if report:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
