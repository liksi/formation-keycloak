#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JAVA_HOME="${JAVA_HOME:-${HOME}/.sdkman/candidates/java/current}"
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

echo "=== Audit dépendances Maven (api) ==="
mvn -f "$ROOT/api/pom.xml" org.codehaus.mojo:versions-maven-plugin:display-dependency-updates -DgenerateBackupPoms=false 2>&1 | grep -E '^\s+.*\->' || echo "  (aucune màj trouvée)"

echo ""
echo "=== Audit dépendances Maven (secret-webapp) ==="
mvn -f "$ROOT/secret-webapp/pom.xml" org.codehaus.mojo:versions-maven-plugin:display-dependency-updates -DgenerateBackupPoms=false 2>&1 | grep -E '^\s+.*\->' || echo "  (aucune màj trouvée)"

echo ""
echo "=== Audit dépendances Maven (provider) ==="
mvn -f "$ROOT/keycloak/provider/pom.xml" org.codehaus.mojo:versions-maven-plugin:display-dependency-updates -DgenerateBackupPoms=false 2>&1 | grep -E '^\s+.*\->' || echo "  (aucune màj trouvée)"

echo ""
echo "=== Audit dépendances npm (vue-app) ==="
cd "$ROOT/vue-app" && npx npm-check-updates --format lines 2>&1 || echo "  npm-check-updates non installé"

echo ""
echo "=== Audit terminé ==="
