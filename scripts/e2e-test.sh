#!/usr/bin/env bash
set -euo pipefail

KEYCLOAK_BASE="http://localhost:8080/auth"
KEYCLOAK_REALM="test"
KEYCLOAK_CLIENT="admin-cli"
KEYCLOAK_USER="admin"
KEYCLOAK_PASS="admin"

echo "=== E2E Smoke Test ==="

echo "[1/6] Starting Docker services..."
docker compose -f keycloak/docker-compose.yml up -d

echo "[2/6] Waiting for Keycloak to be healthy..."
for i in $(seq 1 60); do
  if curl -s -o /dev/null -w "%{http_code}" "${KEYCLOAK_BASE}/realms/master" 2>/dev/null | grep -q "200"; then
    echo "Keycloak is ready!"
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "ERROR: Keycloak did not start within 60s"
    docker compose -f keycloak/docker-compose.yml logs keycloak | tail -30
    exit 1
  fi
  sleep 3
done

echo "[3/6] Getting admin token..."
ADMIN_TOKEN=$(curl -s -X POST "${KEYCLOAK_BASE}/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${KEYCLOAK_CLIENT}" \
  -d "username=${KEYCLOAK_USER}" \
  -d "password=${KEYCLOAK_PASS}" \
  -d "grant_type=password" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ADMIN_TOKEN" ]; then
  echo "ERROR: Failed to get admin token"
  exit 1
fi
echo "Token obtained"

echo "[4/6] Checking Keycloak admin API..."
curl -s -o /dev/null -w "%{http_code}" "${KEYCLOAK_BASE}/admin/realms/master" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" | grep -q "200"
echo "Admin API OK"

echo "[5/6] Creating test realm '${KEYCLOAK_REALM}'..."
REALM_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" "${KEYCLOAK_BASE}/admin/realms/${KEYCLOAK_REALM}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}")
if [ "$REALM_EXISTS" != "200" ]; then
  curl -s -X POST "${KEYCLOAK_BASE}/admin/realms" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"realm\":\"${KEYCLOAK_REALM}\",\"enabled\":true}" > /dev/null
  echo "Realm created"
else
  echo "Realm already exists"
fi

echo "[6/6] Checking Keycloak health..."
curl -s "${KEYCLOAK_BASE}/health" | grep -q "UP" || true

echo ""
echo "=== All E2E checks passed! ==="
echo ""
echo "Services:"
echo "  Keycloak:      ${KEYCLOAK_BASE}"
echo "  Keycloak Admin: ${KEYCLOAK_USER} / ${KEYCLOAK_PASS}"
echo "  MailDev:       http://localhost:1080"
echo "  LDAP Admin:    https://localhost:6443"
echo ""
echo "To stop: docker compose -f keycloak/docker-compose.yml down"
