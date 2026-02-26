# Self-Healing Chaos Agent — Demo Video Script

> **Target Length:** 60-90 seconds
> **Purpose:** Showcase the autonomous chaos → heal → verify loop

---

## Intro (0:00–0:10)

**[Show browser at http://localhost:8080]**

> "This is Online Boutique — a microservices e-commerce app with 12 services."

**[Click through: browse products, add to cart, show cart]**

> "Right now, everything works perfectly. Let's break it."

---

## Health Check (0:10–0:20)

**[Split terminal and browser]**

```bash
./chaos-agent/healthcheck.sh
```

> "All 12 services are green. Let's inject some chaos."

---

## Inject Chaos (0:20–0:35)

**[Terminal: Run chaos injection]**

```bash
python3 chaos-agent/chaos_injector.py kill redis-cart
```

> "We just killed Redis. The cart service now has no database."

**[Switch to browser, refresh, try to view cart]**

> "And... the cart is broken. Users see errors."

**[Terminal: Show observe report]**

```bash
python3 chaos-agent/observe.py report
```

> "Our observer detected the failure and generated a structured report for the AI agent."

---

## AI Healer Agent (0:35–0:50)

**[Terminal: Show the failure report briefly]**

```bash
cat chaos-agent/reports/current_scenario.json | head -20
```

> "The report tells the AI: 'Cart service can't connect to Redis. Expected fix: retry with backoff.'"

**[Show the code diff]**

```bash
git diff --stat HEAD~1
```

> "The Healer Agent patched the C# cart service with exponential backoff and an in-memory fallback cache."

---

## Verification (0:50–1:05)

**[Terminal: Run verification]**

```bash
python3 chaos-agent/verify.py scenario_1_redis_kill
```

> "We rebuild, redeploy, and re-inject the SAME chaos."

**[Wait for output]**

> "This time... the system survives! The cart service retries, then falls back to cache."

---

## Post-Fix Demo (1:05–1:15)

**[Inject chaos again while the fix is in place]**

```bash
python3 chaos-agent/chaos_injector.py kill redis-cart
```

**[Browser: refresh, add to cart]**

> "Even with Redis dead, users can still browse and use cached cart data."

**[Restore Redis]**

```bash
python3 chaos-agent/chaos_injector.py restore redis-cart
```

---

## Closing (1:15–1:30)

**[Show PROGRESS.md]**

```bash
cat PROGRESS.md | head -40
```

> "5 scenarios, 5 resilience patterns, all implemented autonomously."

**[Show scenario status table]**

> "Circuit breakers. Retry with backoff. Graceful degradation. Idempotent payments."

> "This is self-healing infrastructure — powered by AI."

---

## Commands Reference

```bash
# Before demo — make sure everything is running
cd ~/Developer/experiments/microservices-demo
docker compose up -d
cd ~/Developer/experiments/Self\ Healing\ Chaos\ Agent

# Health check
./chaos-agent/healthcheck.sh

# Inject chaos
python3 chaos-agent/chaos_injector.py kill redis-cart
python3 chaos-agent/chaos_injector.py latency currencyservice 3000

# Observe
python3 chaos-agent/observe.py report

# Restore
python3 chaos-agent/chaos_injector.py restore redis-cart
python3 chaos-agent/chaos_injector.py restore currencyservice

# Run full scenario
python3 chaos-agent/run_scenario.py scenario_1_redis_kill

# Verify fix
python3 chaos-agent/verify.py scenario_1_redis_kill
```

---

## Pro Tips

1. **Pre-warm the browser** — Have localhost:8080 loaded before recording
2. **Use tmux/split panes** — Show terminal and browser side-by-side
3. **Font size 18+** — Make sure terminal text is readable
4. **Clear terminals** — `clear` before each command for cleaner recording
5. **Pre-run the scenario once** — So verification passes on camera
