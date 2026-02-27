# Self-Healing Chaos Agent

> **AI agents that automatically detect microservice failures and patch them with resilience patterns.**

A chaos engineering system inspired by [Anthropic's "Building Effective Agents"](https://www.anthropic.com/engineering/building-effective-agents) that uses Claude AI to observe failures in real-time and autonomously implement fixes like retry logic, circuit breakers, and graceful degradation.

<p align="center">
  <img src="https://img.shields.io/badge/AI-Claude-blueviolet?style=for-the-badge" alt="Claude AI"/>
  <img src="https://img.shields.io/badge/Target-Online%20Boutique-green?style=for-the-badge" alt="Online Boutique"/>
  <img src="https://img.shields.io/badge/Chaos-Engineering-red?style=for-the-badge" alt="Chaos Engineering"/>
</p>

---

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   INJECT    │ ──▶ │   OBSERVE   │ ──▶ │    HEAL     │ ──▶ │   VERIFY    │
│   Chaos     │     │   Failures  │     │   with AI   │     │    Fix      │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
  Kill services      Parse logs &       Claude reads        Re-inject same
  Add latency       detect errors       failure report      chaos attack
  Corrupt DNS      Generate report      Patches code       System survives
```

The system runs an autonomous loop:
1. **Inject** chaos (kill containers, add latency, drop packets)
2. **Observe** failures across the microservice mesh
3. **Heal** by having an AI agent read the failure report and implement resilience patterns
4. **Verify** the fix by re-injecting the same chaos

---

## Architecture

```mermaid
flowchart TB
    subgraph "Chaos Engineering Loop"
        CI[chaos_injector.py] -->|"kill/latency/dns"| MS
        MS -->|logs| OB[observe.py]
        OB -->|failure report| HA[Healer Agent]
        HA -->|code patch| MS
        VE[verify.py] -->|re-test| MS
    end

    subgraph MS["Online Boutique (12 services)"]
        FE[Frontend<br/>Go]
        CS[Cart Service<br/>C#]
        RD[(Redis)]
        CU[Currency<br/>Node.js]
        PY[Payment<br/>Node.js]
        SH[Shipping<br/>Go]
        CH[Checkout<br/>Go]
        RC[Recommend<br/>Python]
        AD[Ad Service<br/>Java]
        PC[Product Catalog<br/>Go]
        EM[Email<br/>Python]

        FE --> CS
        FE --> CU
        FE --> RC
        FE --> AD
        CS --> RD
        CH --> PY
        CH --> SH
        CH --> EM
    end

    subgraph "Agent System"
        HA -->|commit| GIT[(Git)]
        RA[Reviewer Agent] -->|review| GIT
        GIT --> VE
    end
```

---

## The Agent Team

| Agent | Role | What It Does |
|-------|------|--------------|
| **Healer** | Fix failures | Reads failure reports, identifies root cause, patches source code with resilience patterns |
| **Reviewer** | Code review | Reviews healer's patches for correctness, bounded retries, proper error handling |

Both agents coordinate through:
- **PROGRESS.md** — Shared state tracker
- **current_tasks/** — File-based task locking
- **Git commits** — Versioned fixes with clear messages

---

## Resilience Patterns

The AI agents implement these battle-tested patterns:

| Pattern | When to Use | Example |
|---------|-------------|---------|
| **Retry with Exponential Backoff** | Transient connection failures | Start 100ms, double each retry, max 5, add jitter |
| **Circuit Breaker** | Latency/timeout issues | Track failures, open after N, half-open after timeout |
| **Graceful Degradation** | Non-critical dependency down | Return defaults/empty instead of 500 |
| **Timeout with Deadline** | Prevent hanging calls | Explicit gRPC/HTTP timeouts |
| **Bulkhead Isolation** | Prevent cascade failures | Separate thread/goroutine pools |
| **Idempotency** | Payment/state changes | Use idempotency keys on retry |

---

## Scenario Results

All 5 chaos scenarios were run end-to-end. Each one injected a real failure, the AI agent diagnosed it, patched the source code, and the fix was verified by re-injecting the same chaos.

---

### Scenario 1: Redis Kill

| | |
|---|---|
| **Target** | `redis-cart` (Redis backing the Cart Service) |
| **Attack** | `docker kill` on Redis container |
| **What broke** | Cart Service (C#) threw `RedisConnectionException` on every request |
| **AI diagnosis** | `cartservice cannot connect to a downstream dependency` |
| **Fix applied** | Retry with exponential backoff + in-memory fallback cache |
| **File patched** | `src/cartservice/src/` |
| **Result** | **PASSED** — system survived Redis being down |

<details>
<summary>Verification output</summary>

```json
{
  "scenario": "scenario_1_redis_kill",
  "scenario_name": "Redis Cart Kill",
  "chaos_survived": true,
  "dependent_failures": [],
  "system_status_under_chaos": "DEGRADED",
  "expected_pattern": "retry with exponential backoff + in-memory fallback"
}
```
</details>

<details>
<summary>Code fix — Retry with exponential backoff (C#)</summary>

```csharp
// Retry with exponential backoff
private async Task<T> RetryWithBackoff<T>(Func<Task<T>> operation)
{
    int retries = 0;
    while (retries < MaxRetries)
    {
        try { return await operation(); }
        catch (RedisConnectionException)
        {
            retries++;
            var delay = InitialDelay * Math.Pow(2, retries) + Random.Next(100);
            await Task.Delay((int)delay);
        }
    }
    return _fallbackCache.GetOrDefault(key); // Graceful degradation
}
```
</details>

---

### Scenario 2: Currency Latency

| | |
|---|---|
| **Target** | `currencyservice` (Node.js) |
| **Attack** | 3000ms latency injected via `tc netem` |
| **What broke** | Frontend and Checkout hung waiting for currency conversion |
| **AI diagnosis** | `currencyservice experiencing high latency` |
| **Fix applied** | Circuit breaker with cached currency data |
| **File patched** | `src/currencyservice/server.js` |
| **Result** | **PASSED** — frontend used cached rates when circuit opened |

<details>
<summary>Verification output</summary>

```json
{
  "scenario": "scenario_2_latency",
  "chaos_survived": true,
  "dependent_failures": [],
  "system_status_under_chaos": "DEGRADED",
  "fix_applied": {
    "target": "src/currencyservice/server.js",
    "pattern": "circuit_breaker",
    "description": "Circuit breaker with caching and graceful degradation"
  },
  "verification_notes": "Frontend and checkoutservice continued to function using cached currency data when circuit opened after latency injection"
}
```
</details>

---

### Scenario 3: Payment Kill

| | |
|---|---|
| **Target** | `paymentservice` (Node.js) |
| **Attack** | `docker kill` on Payment Service container |
| **What broke** | Checkout failed at payment step, potential duplicate charges on retry |
| **AI diagnosis** | `checkoutservice cannot reach paymentservice` |
| **Fix applied** | Idempotent retry with exponential backoff and jitter |
| **File patched** | `src/checkoutservice/main.go` |
| **Result** | **PASSED** — retried with idempotency keys, no duplicate charges |

<details>
<summary>Verification output</summary>

```json
{
  "scenario": "scenario_3_payment_kill",
  "chaos_survived": true,
  "dependent_failures": [],
  "system_status_under_chaos": "DEGRADED",
  "fix_applied": {
    "target": "src/checkoutservice/main.go",
    "pattern": "idempotent_retry",
    "description": "Idempotent retry with exponential backoff and jitter"
  },
  "verification_notes": "Checkoutservice retried payment calls with idempotency keys, preventing duplicate charges when payment service was killed and restored"
}
```
</details>

---

### Scenario 4: Shipping Packet Loss

| | |
|---|---|
| **Target** | `shippingservice` (Go) |
| **Attack** | 50% packet loss via `tc netem` |
| **What broke** | Checkout intermittently failed to get shipping quotes and ship orders |
| **AI diagnosis** | `shippingservice experiencing packet loss` |
| **Fix applied** | Retry with exponential backoff for `quoteShipping` and `shipOrder` |
| **File patched** | `src/checkoutservice/main.go` |
| **Result** | **PASSED** — completed shipping despite 50% packet loss |

<details>
<summary>Verification output</summary>

```json
{
  "scenario": "scenario_4_shipping_packetloss",
  "chaos_survived": true,
  "dependent_failures": [],
  "system_status_under_chaos": "DEGRADED",
  "fix_applied": {
    "target": "src/checkoutservice/main.go",
    "pattern": "retry_with_backoff",
    "description": "Retry with exponential backoff for quoteShipping and shipOrder"
  },
  "verification_notes": "Checkoutservice successfully completed shipping operations despite 50% packet loss through retry mechanism"
}
```
</details>

---

### Scenario 5: Recommendation Crash

| | |
|---|---|
| **Target** | `recommendationservice` (Python) |
| **Attack** | `docker kill` on Recommendation Service |
| **What broke** | Frontend returned 500 errors when fetching product recommendations |
| **AI diagnosis** | `recommendationservice is down` |
| **Fix applied** | Graceful degradation with product caching |
| **File patched** | `src/recommendationservice/recommendation_server.py` |
| **Result** | **PASSED** — frontend rendered pages without recommendations, no 500s |

<details>
<summary>Verification output</summary>

```json
{
  "scenario": "scenario_5_recommendation_crash",
  "chaos_survived": true,
  "dependent_failures": [],
  "system_status_under_chaos": "DEGRADED",
  "fix_applied": {
    "target": "src/recommendationservice/recommendation_server.py",
    "pattern": "graceful_degradation",
    "description": "Graceful degradation with product caching"
  },
  "verification_notes": "Frontend displayed pages without recommendations when recommendation service was killed - no 500 errors propagated"
}
```
</details>

---

### Summary

| Scenario | Attack | Language | Pattern | Result |
|----------|--------|----------|---------|--------|
| Redis Kill | `docker kill` | C# | Retry + fallback cache | **PASSED** |
| Currency Latency | 3s `tc netem` | Node.js | Circuit breaker | **PASSED** |
| Payment Kill | `docker kill` | Go | Idempotent retry | **PASSED** |
| Shipping Packet Loss | 50% `tc netem` | Go | Retry with backoff | **PASSED** |
| Recommendation Crash | `docker kill` | Python | Graceful degradation | **PASSED** |

> All 5 scenarios: chaos injected, AI diagnosed, code patched, fix verified. Zero manual intervention.

---

## Quick Start

### Prerequisites

```bash
docker --version          # Docker 24+
docker compose version    # Docker Compose v2+
python3 --version         # Python 3.10+
```

### 1. Clone and Start Services

```bash
git clone https://github.com/zeelp741/Self-Healing-Chaos-Agent.git
cd self-healing-chaos-agent

# Clone Online Boutique (target microservices)
git clone https://github.com/GoogleCloudPlatform/microservices-demo.git ../microservices-demo

# Start all services (first build takes 10-20 min)
cd ../microservices-demo
docker compose build && docker compose up -d

# Verify everything is running
cd ../self-healing-chaos-agent
./chaos-agent/healthcheck.sh
```

### 2. Inject Chaos

```bash
# Kill Redis (Cart Service will fail)
python3 chaos-agent/chaos_injector.py kill redis-cart

# Add 3 seconds latency to Currency Service
python3 chaos-agent/chaos_injector.py latency currencyservice 3000

# Restore a service
python3 chaos-agent/chaos_injector.py restore redis-cart
```

### 3. Observe Failures

```bash
# One-time failure report
python3 chaos-agent/observe.py report

# Continuous monitoring
python3 chaos-agent/observe.py monitor --interval 15
```

### 4. Run a Full Scenario

```bash
# Inject → Wait → Observe → Generate Report
python3 chaos-agent/run_scenario.py scenario_1_redis_kill

# Verify a fix works
python3 chaos-agent/verify.py scenario_1_redis_kill
```

### 5. Run the AI Agents (requires Claude Code CLI)

```bash
# Run the Healer Agent
./chaos-agent/harness.sh healer

# Run the Reviewer Agent (in another terminal)
./chaos-agent/harness.sh reviewer
```

---

## Project Structure

```
self-healing-chaos-agent/
├── chaos-agent/
│   ├── chaos_injector.py    # Inject failures (kill, latency, packetloss, dns)
│   ├── observe.py           # Monitor services, generate LLM-optimized reports
│   ├── run_scenario.py      # Orchestrate inject → wait → observe → report
│   ├── verify.py            # Rebuild, redeploy, re-test after a fix
│   ├── harness.sh           # Agent loop runner
│   ├── healthcheck.sh       # Quick health check all services
│   ├── HEALER_PROMPT.md     # Instructions for healing agent
│   └── REVIEWER_PROMPT.md   # Instructions for reviewer agent
└── README.md
```

---


## Observability Design

The `observe.py` output is optimized for LLM consumption:

```
============================================================
SYSTEM STATUS: DEGRADED
TIMESTAMP: 2026-02-22T10:30:45
HEALTHY: frontend, productcatalogservice, adservice
------------------------------------------------------------
ERROR | service=cartservice | lang=C# | status=ERRORS | errors=12 |
       cause=cartservice cannot connect to a downstream dependency
------------------------------------------------------------
ACTION: Add retry with exponential backoff in src/cartservice/src/
        for cartservice (C#) when connecting to downstream services
============================================================
```

Key principles:
- Max 10-line summaries (no log flooding)
- Pre-computed likely cause
- File paths for relevant source code
- Deduplicated error types
- Recommended actions

---

## Hardware Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 16 GB | 24 GB |
| Disk | 10 GB | 20 GB |
| CPU | 4 cores | 8 cores |

---

## Inspiration

This project was inspired by Anthropic's engineering blog posts on building effective AI agents, particularly their approach of:

- **Tight feedback loops** — inject chaos, observe immediately
- **LLM-optimized output** — no log flooding, pre-computed diagnosis
- **Agent coordination** — file-based task locking, shared progress tracking
- **Verification-driven development** — every fix is re-tested against the same chaos

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-scenario`)
3. Commit your changes (`git commit -m 'Add scenario for database failures'`)
4. Push to the branch (`git push origin feature/new-scenario`)
5. Open a Pull Request

---

## License

MIT License — feel free to use this for learning, demos, or building your own chaos engineering systems.

---

<p align="center">
  Built with Claude AI and a healthy disrespect for uptime.
</p>
