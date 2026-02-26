# FORZEEL.md — The Story Behind Self-Healing Chaos Agent

> A deep dive into how this chaos engineering system works, why it was built this way, and what you can learn from it.

---

## What Is This Project, Really?

Imagine you're running an e-commerce site during Black Friday. Suddenly, your cache server crashes. In the old days, your entire checkout flow would collapse, customers would see error pages, and you'd lose thousands of dollars per minute while your on-call engineer scrambles to fix it.

This project flips that script. Instead of humans racing to diagnose and patch failures, **AI agents do it automatically**.

The system:
1. Intentionally breaks things (kills containers, adds network latency)
2. Watches what fails
3. Has an AI read the failure report and patch the source code
4. Verifies the fix actually works
5. Repeats

It's like having a junior engineer who never sleeps, can read error logs in milliseconds, and knows every resilience pattern from the Site Reliability Engineering handbook.

---

## The Architecture: Why It's Built This Way

### The Target: Online Boutique

We didn't build a toy system to break. We use [Google's Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo) — a real e-commerce demo with 11 microservices written in 6 different languages:

| Service | Language | Why It Matters |
|---------|----------|----------------|
| Frontend | Go | Entry point, depends on everything |
| Cart Service | C# | Stateful (uses Redis), first target for chaos |
| Currency Service | Node.js | Stateless but slow = timeout chaos |
| Payment Service | Node.js | Critical path, needs idempotency |
| Checkout | Go | Orchestrator, calls 5 downstream services |
| Recommendation | Python | Non-critical, perfect for graceful degradation |
| Ad Service | Java | Heavy JVM startup, interesting failure modes |

This diversity is intentional. Real systems have polyglot architectures. An AI agent that can only fix Python code is useless when your C# cart service crashes.

### The Chaos Injector

```
chaos_injector.py kill redis-cart
```

This command looks simple, but there's philosophy behind it:

**Why container kills instead of code-level faults?**
- Container death is the most common production failure
- It tests the *entire* failure path (network, discovery, retries)
- No need to instrument the target code

**Why network latency injection?**
- Latency is the silent killer — services often hang waiting forever
- It exposes missing timeouts and circuit breakers
- Uses Linux `tc` (traffic control) — production-grade network manipulation

**Why DNS corruption?**
- Modern systems resolve hostnames constantly
- Cached DNS can mask infrastructure issues
- Tests service discovery resilience

### The Observer: Making AI Work

Here's where we learned the most important lesson:

> **Raw logs are useless for AI agents.**

Our first version of `observe.py` just dumped 500 lines of container logs into the prompt. Claude would spend 80% of its context window reading "INFO: Request received at 10:32:45" messages and miss the actual error.

The fix was to **pre-compute the diagnosis**:

```python
def suggest_likely_cause(service, errors, container_status):
    if not container_status["running"]:
        return f"Container {service} is DOWN (crashed or stopped)"

    error_types = [e["type"] for e in errors]

    if "connection_refused" in error_types:
        return f"{service} cannot connect to a downstream dependency"
    if "timeout" in error_types:
        return f"{service} is experiencing timeouts (possible network latency)"
```

The output is now:
- Max 10 lines
- Pre-computed likely cause
- File paths for relevant source code
- Deduplicated errors (only 3 unique samples)
- Specific recommended actions

This is the difference between giving someone a phone book and giving them a name and number.

### The Agent Harness: Coordination Without Complexity

With multiple AI agents (Healer, Reviewer), we needed coordination. Our first instinct was to build a message queue, database, or API server.

**We didn't.**

Instead, we use:
- **PROGRESS.md** — A markdown file both agents read/write
- **current_tasks/** — Empty files as locks (create file = claim task)
- **Git commits** — The universal record of changes

Why this approach?

1. **Debuggability** — Every state is a text file you can read
2. **No moving parts** — No database to crash, no API to timeout
3. **Git as truth** — Every fix is versioned, reviewable, revertable
4. **Human-compatible** — You can manually edit PROGRESS.md if an agent gets stuck

This is a pattern from Anthropic's engineering blog: "file-based state is surprisingly robust for single-machine multi-agent systems."

---

## The Resilience Patterns: A Mini SRE Handbook

The AI agents don't invent new patterns. They implement well-known resilience techniques. Here's what each one does and when to use it:

### 1. Retry with Exponential Backoff

**The Problem:** Transient failures (network blip, brief overload) often resolve themselves in milliseconds.

**The Pattern:**
```
Attempt 1: Wait 100ms
Attempt 2: Wait 200ms
Attempt 3: Wait 400ms
Attempt 4: Wait 800ms
Attempt 5: Give up
```

**Why exponential?** Linear retry (wait 1s, wait 1s, wait 1s) creates "thundering herd" — all clients retry simultaneously after the same delay, re-overwhelming the server.

**Why jitter?** Even with exponential backoff, synchronized retries can spike. Adding random jitter (e.g., ±50ms) spreads the load.

### 2. Circuit Breaker

**The Problem:** A slow downstream service is worse than a dead one. Slow calls tie up threads, exhaust connection pools, and cascade failures upstream.

**The Pattern:**
```
CLOSED (normal) → failures accumulate → OPEN (fast-fail all requests)
                                              ↓
                                        wait 30 seconds
                                              ↓
                              HALF-OPEN (try one request)
                                     ↓              ↓
                              success: CLOSED    failure: OPEN
```

**The insight:** "Fail fast" is a feature. It's better to return an error immediately than wait 30 seconds for a timeout.

### 3. Graceful Degradation

**The Problem:** Not all failures are equal. If the recommendation service dies, should your entire homepage crash?

**The Pattern:** Return sensible defaults instead of propagating errors.

```python
try:
    recommendations = get_recommendations(user_id)
except RecommendationServiceDown:
    recommendations = []  # Show "Popular Items" instead
```

**The art:** Knowing which services are critical (payment) vs. nice-to-have (recommendations).

### 4. Idempotency

**The Problem:** Payment processing with retries. What if the retry succeeds but the first attempt also succeeded? Customer charged twice.

**The Pattern:** Idempotency keys.

```
POST /charge
{
  "amount": 99.99,
  "idempotency_key": "order-12345-attempt-1"
}
```

The payment service records each key. If it sees the same key twice, it returns the previous result instead of charging again.

---

## Bugs We Ran Into (And How We Fixed Them)

### Bug 1: ARM64 gRPC Tools

**Symptom:** Cart service build failed on Apple Silicon Macs.

**Root cause:** The gRPC tools NuGet package doesn't have ARM64 binaries.

**Fix:** Added `platform: linux/amd64` to docker-compose.yaml, forcing x86 emulation.

**Lesson:** Container cross-architecture is not solved. Always test builds on your actual deployment target.

### Bug 2: Missing Service Address

**Symptom:** Frontend crashed immediately with "SHOPPING_ASSISTANT_SERVICE_ADDR not set".

**Root cause:** Online Boutique added a new service (GenAI shopping assistant) but our docker-compose didn't include it.

**Fix:** Set `SHOPPING_ASSISTANT_SERVICE_ADDR: "localhost:0"` — a valid address that fails gracefully.

**Lesson:** When integrating external projects, watch for new required config between versions.

### Bug 3: False Positive Error Detection

**Symptom:** observe.py reported errors even when the system was healthy.

**Root cause:** Log lines like `"error_count": 0` matched our "error" regex pattern.

**Fix:** More specific patterns and explicit skip rules:
```python
# Skip resilience log lines (these are good, not errors)
if any(tag in line for tag in ["[RETRY]", "[FALLBACK]", "[RESILIENCE]"]):
    continue
```

**Lesson:** Log parsing is fragile. Either use structured logging (JSON with explicit severity fields) or be very defensive about false positives.

### Bug 4: Docker Compose Path Issues

**Symptom:** observe.py couldn't find containers when run from the chaos-agent directory.

**Root cause:** `docker compose ps` looks for docker-compose.yaml relative to current working directory.

**Fix:** Added explicit `cwd=REPO_DIR` to all subprocess calls.

**Lesson:** Scripts that shell out are sensitive to cwd. Make paths explicit.

---

## How Good Engineers Think About This

### 1. Start with Observability

We didn't start by writing the AI agent. We started by building `observe.py` — the tool that generates failure reports.

Why? Because **if you can't see failures clearly, you can't fix them reliably**. This applies to humans and AI alike.

The observe → act loop is the foundation. Get the observe part right first.

### 2. Make State Visible

Every piece of system state lives in a human-readable file:
- PROGRESS.md — What's done, what's not
- current_tasks/ — Who's working on what
- reports/*.json — What failures were observed
- verification_results/*.json — Did fixes work?

This isn't just for debugging. It's a design philosophy: **invisible state is untestable state**.

### 3. Verification Closes the Loop

The `verify.py` script isn't just a nice-to-have. It's the difference between "we think we fixed it" and "we know we fixed it."

The verification loop:
1. Rebuild the patched service
2. Redeploy to Docker
3. Wait for stability
4. Re-inject the exact same chaos
5. Check if dependent services survive

Without verification, you're just hoping.

### 4. Constrain the AI, Don't Trust It

The agent prompts are full of explicit constraints:

```markdown
## Rules

- Only modify files in the service identified in the failure report
- Keep changes minimal — add the resilience pattern, don't refactor
- Do NOT add dependencies unless absolutely necessary
- Do NOT modify the gRPC proto files
```

Why? Because AI agents will "improve" things if you let them. They'll refactor working code, add unnecessary abstractions, and make changes that look good in isolation but break the system.

**Tight constraints → predictable behavior → debuggable systems.**

### 5. File-Based Coordination is Underrated

When people hear "multi-agent system" they think Kubernetes, message queues, distributed databases.

We use:
- Text files
- Git

It works surprisingly well for single-machine systems. The agents don't need real-time coordination — they need to not step on each other's work. File locks and a shared markdown file are enough.

---

## What You Could Build Next

### Extend the Scenarios

Add chaos scenarios for:
- **Database failures** (PostgreSQL connection pool exhaustion)
- **Memory pressure** (OOM killer targeting specific services)
- **Clock skew** (time-based bugs, JWT expiry chaos)
- **TLS certificate expiry** (mTLS failures between services)

### Add More Agent Roles

- **Docs Agent** — Auto-generates runbooks from successful fixes
- **Rollback Agent** — Reverts changes if verification fails
- **Capacity Agent** — Analyzes if failures are due to undersizing

### Connect to Real Monitoring

Replace log-based observation with:
- Prometheus metrics
- Jaeger traces
- Real APM data

This is more production-realistic but requires instrumenting the target services.

### Multi-Repository Fixes

Online Boutique is a monorepo. Real systems have separate repos per service. Extend the agent to:
1. Identify which repo contains the failing service
2. Clone and branch
3. Open a PR (not just commit)
4. Await review before merging

---

## Final Thoughts

This project demonstrates that AI agents can do useful, non-trivial engineering work — but only when you:

1. **Give them good information** (pre-computed diagnostics, not log dumps)
2. **Constrain their scope** (fix this file, use this pattern)
3. **Verify their work** (automated testing, not trust)
4. **Make state visible** (text files, git, readable formats)

The future of AI-assisted engineering isn't replacing developers. It's building systems where AI handles the predictable parts (retry logic, timeout configuration) while humans handle the unpredictable parts (novel failure modes, architectural decisions).

This chaos agent is a small step in that direction.

---

*Built by experimenting, breaking things, and learning from the failures — just like the system itself.*
