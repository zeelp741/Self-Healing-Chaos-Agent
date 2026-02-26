# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Self-Healing Chaos Agent is a chaos engineering system that uses AI agents to automatically detect failures in microservices and patch them with resilience patterns. It targets Google's Online Boutique microservices demo, running locally via Docker Compose.

The system follows a loop: inject chaos → observe failures → heal with code patches → verify fix → repeat.

## Architecture

```
chaos-agent/
├── chaos_injector.py    # Injects failures (kill, latency, packetloss, dns)
├── observe.py           # Monitors services, generates failure reports for LLM consumption
├── run_scenario.py      # Orchestrates inject → wait → observe → report
├── verify.py            # Rebuilds, redeploys, re-tests after a fix
├── harness.sh           # Agent loop runner (healer/reviewer roles)
├── HEALER_PROMPT.md     # Instructions for the healing agent
└── REVIEWER_PROMPT.md   # Instructions for the code review agent
```

**Agent Roles:**
- **Healer Agent**: Reads failure reports, identifies root cause, implements resilience patterns
- **Reviewer Agent**: Reviews healer patches for correctness, bounded retries, proper error handling

## Commands

```bash
# Docker Compose (Online Boutique)
docker compose build                           # Build all services (10-20 min first time)
docker compose up -d                           # Start all services
docker compose ps                              # Check container status

# Health Check
./chaos-agent/healthcheck.sh                   # Quick health check all services

# Chaos Injection
python3 chaos-agent/chaos_injector.py kill <service>
python3 chaos-agent/chaos_injector.py latency <service> <ms>
python3 chaos-agent/chaos_injector.py packetloss <service> <percent>
python3 chaos-agent/chaos_injector.py dns <service>
python3 chaos-agent/chaos_injector.py restore <service>

# Observability
python3 chaos-agent/observe.py report          # One-time failure report
python3 chaos-agent/observe.py monitor         # Continuous monitoring

# Scenarios
python3 chaos-agent/run_scenario.py <scenario_id>     # Run full scenario
python3 chaos-agent/verify.py <scenario_id>           # Verify a fix works

# Agent Harness
./chaos-agent/harness.sh healer                # Run healer agent loop
./chaos-agent/harness.sh reviewer              # Run reviewer agent loop
```

## Predefined Scenarios

| ID | Target | Attack | Expected Fix |
|----|--------|--------|--------------|
| scenario_1_redis_kill | redis-cart | kill | Retry with exponential backoff in C# cartservice |
| scenario_2_latency | currencyservice | 3s latency | Circuit breaker in Node.js |
| scenario_3_payment_kill | paymentservice | kill | Idempotent retry |
| scenario_5_recommendation_crash | recommendationservice | kill | Graceful degradation (return empty) |

## Resilience Patterns

The Healer agent implements these patterns:
- **Retry with exponential backoff**: Start 100ms, double each retry, max 5, add jitter
- **Circuit breaker**: Track failures, open after N failures, half-open after timeout
- **Graceful degradation**: Return defaults/empty instead of propagating errors
- **Timeout with deadline**: Explicit timeouts on gRPC/HTTP calls
- **Bulkhead isolation**: Isolate downstream calls in separate thread/goroutine pools
- **Idempotency**: Use idempotency keys for payment/state-changing operations

## Observability Design

The observe.py output is optimized for LLM consumption:
- Max 10-line summaries
- Pre-computed likely cause
- File paths for relevant source code
- Deduplicated error types
- Sample errors (max 3 unique)
- Recommended actions

## Progress Tracking

- `PROGRESS.md`: Agent-maintained status of scenarios (PENDING/IN_PROGRESS/COMPLETED)
- `current_tasks/`: Task lock directory for multi-agent coordination
- `agent_logs/`: Session logs from agent runs
- `verification_results/`: JSON results from verify.py

## Claude Code Custom Commands

| Command | Purpose |
|---------|---------|
| /ralph-loop | Autonomous implementation loop with completion promise |
| /plan-feature | Create detailed implementation plan for new features |

## Hardware Requirements

- RAM: 16GB minimum (11 containers + Redis + scripts)
- Disk: ~10GB for container images
- CPU: 4+ cores recommended

## Agent Team Structure

This project is designed to be built with Claude Code Agent Teams. Each teammate owns a distinct set of files with no overlap:

| Teammate | Owns | Files |
|----------|------|-------|
| **infra** | Docker setup | `docker-compose.yaml`, service Dockerfiles |
| **chaos** | Chaos injection | `chaos-agent/chaos_injector.py` |
| **observer** | Observability | `chaos-agent/observe.py`, `chaos-agent/run_scenario.py` |
| **harness** | Agent loop | `chaos-agent/harness.sh`, `chaos-agent/verify.py`, `chaos-agent/HEALER_PROMPT.md`, `chaos-agent/REVIEWER_PROMPT.md` |
| **docs** | Documentation | `PROGRESS.md`, `README.md`, `chaos-agent/healthcheck.sh` |

### Task Dependencies

```
Phase 1 (infra): Fork repo, create docker-compose.yaml, verify services run
    ↓
Phase 2 (chaos): Build chaos_injector.py, add NET_ADMIN to containers
    ↓
Phase 3 (observer): Build observe.py, run_scenario.py ← depends on chaos working
    ↓
Phase 4 (harness): Build harness.sh, prompts, verify.py ← depends on observer
    ↓
Phase 5: Run scenarios autonomously ← all teammates verify together
```

### Starting the Team

```
Create an agent team to build the Self-Healing Chaos Agent. Read CLAUDE.md and
IMPLEMENTATION_PLAN.md for full context. Spawn 4 teammates:

1. infra: Set up Docker Compose for Online Boutique (Phase 1)
2. chaos: Build chaos_injector.py with kill/latency/packetloss/dns attacks (Phase 2)
3. observer: Build observe.py and run_scenario.py (Phase 3, after chaos)
4. harness: Build harness.sh, verify.py, and agent prompts (Phase 4, after observer)

Require plan approval before teammates make changes. Coordinate task
dependencies - observer depends on chaos working, harness depends on observer.
```
