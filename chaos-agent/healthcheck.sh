#!/bin/bash
# Quick health check for all Online Boutique services
# Usage: ./healthcheck.sh

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "═══════════════════════════════════════════════════════════"
echo "  Online Boutique Health Check"
echo "═══════════════════════════════════════════════════════════"

# Frontend (HTTP)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 2>/dev/null)
if [ "$STATUS" = "200" ]; then
    echo -e "${GREEN}[OK]${NC} Frontend (Go)              - HTTP 200"
else
    echo -e "${RED}[FAIL]${NC} Frontend (Go)              - HTTP $STATUS"
fi

# Check each container is running
# Adjust container name prefix based on your docker-compose project name
PROJECT_PREFIX="${COMPOSE_PROJECT_NAME:-microservices-demo}"

SERVICES=(
    "cartservice:C#"
    "redis-cart:Redis"
    "productcatalogservice:Go"
    "currencyservice:Node.js"
    "paymentservice:Node.js"
    "shippingservice:Go"
    "emailservice:Python"
    "checkoutservice:Go"
    "recommendationservice:Python"
    "adservice:Java"
    "loadgenerator:Python"
)

for entry in "${SERVICES[@]}"; do
    svc="${entry%%:*}"
    lang="${entry##*:}"

    # Try different container naming conventions
    STATE=$(docker inspect -f '{{.State.Status}}' "${PROJECT_PREFIX}-${svc}-1" 2>/dev/null || \
            docker inspect -f '{{.State.Status}}' "${PROJECT_PREFIX}_${svc}_1" 2>/dev/null || \
            docker inspect -f '{{.State.Status}}' "${svc}" 2>/dev/null)

    if [ "$STATE" = "running" ]; then
        printf "${GREEN}[OK]${NC} %-25s - %s\n" "$svc" "$lang"
    else
        printf "${RED}[FAIL]${NC} %-25s - State: %s\n" "$svc" "${STATE:-not found}"
    fi
done

echo "═══════════════════════════════════════════════════════════"

# Summary
RUNNING=$(docker compose ps --format json 2>/dev/null | grep -c '"running"' || echo "0")
echo -e "\nContainers running: ${RUNNING}"
echo "Frontend URL: http://localhost:8080"
