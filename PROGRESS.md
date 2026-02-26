# Self-Healing Chaos Agent — Progress Tracker

> This file is maintained by the AI agents. Each agent reads this on startup
> to orient itself, and updates it before exiting.

## Build Status

| Phase | Component | Status | Notes |
|-------|-----------|--------|-------|
| 1 | Fork Online Boutique | **DONE** | Cloned to ../microservices-demo |
| 1 | Run docker-compose | **DONE** | All 12 services running |
| 1 | Verify services run | **DONE** | Frontend at http://localhost:8080, healthcheck.sh green |
| 2 | chaos_injector.py | **DONE** | kill, latency, packetloss, dns, restore |
| 2 | healthcheck.sh | **DONE** | Quick status check |
| 2 | Verify attacks work | **DONE** | kill ✓, latency ✓ (6.2s delay), restore ✓, JSON output ✓ |
| 3 | observe.py | **DONE** | LLM-optimized failure reports |
| 3 | run_scenario.py | **DONE** | 5 predefined scenarios |
| 3 | Verify observe/scenario | **DONE** | Tested inject → wait → report loop ✓ |
| 4 | HEALER_PROMPT.md | **DONE** | Healer agent instructions |
| 4 | REVIEWER_PROMPT.md | **DONE** | Reviewer agent instructions |
| 4 | harness.sh | **DONE** | Agent loop runner |
| 4 | verify.py | **DONE** | Verification pipeline (tested rebuild → inject → check) |
| 4 | current_tasks/ | **DONE** | Directory for task locking created |

## Scenario Status

| Scenario | Status | Agent | Commit | Verification |
|----------|--------|-------|--------|--------------|
| scenario_1_redis_kill | **COMPLETED** | Healer | pending | PASSED ✓ |
| scenario_2_latency | PENDING | — | — | — |
| scenario_3_payment_kill | PENDING | — | — | — |
| scenario_4_shipping_packetloss | PENDING | — | — | — |
| scenario_5_recommendation_crash | PENDING | — | — | — |

## Completed Work

- 2024: All chaos tooling built (chaos_injector, observe, run_scenario, harness, verify)
- Agent prompts created (HEALER_PROMPT.md, REVIEWER_PROMPT.md)
- 2026-02-21: **Phase 1 Complete** — Online Boutique running locally via Docker Compose (12 containers)
- 2026-02-21: **Phase 2 Complete** — Chaos injection verified (kill stops services, latency adds 3s delay, restore works)
- 2026-02-21: **Phase 3 Complete** — Observability layer verified (observe.py, run_scenario.py work end-to-end)
- 2026-02-21: **Phase 4 Complete** — Agent harness verified (verify.py pipeline works, prompts ready)
- 2026-02-22: **Scenario 1 Complete** — Redis Kill resilience fix in cartservice (C#)
  - Added retry with exponential backoff (3 retries, 100ms initial, 2x multiplier, jitter)
  - Added in-memory fallback cache (ConcurrentDictionary)
  - Circuit breaker pattern (tracks Redis availability, periodic re-check)
  - Graceful degradation (returns empty cart instead of 500 error)
  - File: `src/cartservice/src/cartstore/RedisCartStore.cs`

## Failed Attempts

(None yet)

## Notes for Next Agent

**Infrastructure is ready!**

- Online Boutique running at http://localhost:8080
- All 12 containers healthy (verified 2026-02-21)
- Microservices-demo located at: `/Users/zeelpatel/Developer/experiments/microservices-demo`

**Fixed during setup:**
- Added `platform: linux/amd64` to cartservice (gRPC tools ARM64 bug)
- Set `SHOPPING_ASSISTANT_SERVICE_ADDR: "localhost:0"` (required but unused)
- Added `iproute2` to currencyservice Dockerfile (for tc latency injection)
- Fixed observe.py to use correct docker-compose directory (cwd=REPO_DIR)
- Fixed observe.py error detection patterns to reduce false positives:
  - Skip [RETRY], [FALLBACK], [RESILIENCE] log lines (resilience working, not errors)
  - Skip HTTP 2xx success responses
  - More specific patterns to avoid matching JSON field names

**Ready to run chaos scenarios:**
```bash
python3 chaos-agent/run_scenario.py scenario_1_redis_kill
```
