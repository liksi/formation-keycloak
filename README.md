# Formation Keycloak

Keycloak training workshop by [Liksi](https://www.liksi.fr) — hands-on lab to learn Keycloak, OAuth2/OIDC, and application security.

## Architecture

```
                          ┌─────────────────────┐
                          │    Keycloak 26.6.2    │
                          │  ┌───────────────┐   │
                          │  │ SPI Provider   │   │
                          │  │ • Authenticator│   │
                          │  │ • RequiredAct. │   │
                          │  │ • Mapper       │   │
                          │  └───────────────┘   │
                          └──────────┬───────────┘
                                     │ OAuth2 / OIDC
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
    ┌─────▼──────┐           ┌───────▼───────┐          ┌───────▼───────┐
    │  vue-app   │           │ secret-webapp │          │      api      │
    │  Vue 3     │           │ Spring Boot   │          │  Spring Boot  │
    │  (SPA)     │           │ OAuth2 Client │          │  OAuth2 RS    │
    │  :8070     │           │  :8090        │          │   :8091       │
    └────────────┘           └───────────────┘          └───────────────┘

                              Auxiliary services:
┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐
│PostgreSQL│ │ OpenLDAP │ │ phpLDAPadmin │ │ MailDev  │ │oauth2-   │
│   :5432  │ │ :389:636 │ │    :6443     │ │  :1025   │ │proxy     │
└──────────┘ └──────────┘ └──────────────┘ │  :1080   │ │  :4180   │
                                           └──────────┘ └──────────┘
```

## Prerequisites

- **Docker** and Docker Compose (v2+)
- **Java 25** (Temurin recommended)
- **Maven 3.9+**
- **Node.js 22+** and npm

## Versions

| Component | Version |
|-----------|---------|
| Keycloak | 26.6.2 |
| keycloak-js | 26.2.4 |
| PostgreSQL | 16 |
| Spring Boot | 4.0.6 |
| Spring Security | 7.0.x |
| Java | 25 |
| Vue | 3.5.x |
| Vite | 8.x |
| Vue Router | 5.x |
| Vitest | 4.x |
| oauth2-proxy | 7.15.2 |
| OpenLDAP | 1.5.0 |
| MailDev | 2.1.0 |

## Quick Start — One Command

From the project root, build and start **everything** in one shot:

```bash
docker compose up --build -d
```

This builds and launches all 9 services:

| Service | URL | Notes |
|---------|-----|-------|
| Keycloak | http://localhost:8080 | admin / admin |
| API Resource Server | http://localhost:8091/messages/public | JWT-protected REST API |
| Secret Webapp | http://localhost:8090 | Multi-auth mode webapp |
| Vue App (SPA) | http://localhost:8070 | Keycloak-secured frontend |
| MailDev Web UI | http://localhost:1080 | Catch-all SMTP inbox |
| LDAP Admin (phpLDAPadmin) | https://localhost:6443 | cn=admin,dc=formation / admin |
| oauth2-proxy | http://localhost:4180 | Auth reverse proxy |
| OpenLDAP | localhost:389 | LDAP directory |
| PostgreSQL | localhost:5432 | Keycloak database |

> **Always rebuild**: `docker compose up --build` recompiles all apps from source. Use the `--build` flag every time you change code.

To stop: `docker compose down`

## Development Workflow

During the practical work, you'll modify source code. Use the manual workflow:

### 1. Start infrastructure

```bash
docker compose up -d postgres keycloak openldap phpldapadmin smtp oauth2-proxy
```

### 2. Run apps locally

```bash
# API Resource Server (port 8091)
cd api
mvn spring-boot:run

# Secret Webapp (port 8090, mode configured in application.yml)
cd secret-webapp
mvn spring-boot:run

# Vue App (port 8070)
cd vue-app
npm install
npm run dev
```

### 3. Stop infrastructure

```bash
docker compose down
```

## Ports

| Application | Port | Protocol |
|-------------|------|----------|
| Keycloak HTTP | 8080 | HTTP |
| Keycloak HTTPS | 8443 | HTTPS |
| Keycloak Management | 9990 | HTTP |
| API Resource Server | 8091 | HTTP |
| Secret Webapp | 8090 | HTTP |
| Vue App (dev/build) | 8070 | HTTP |
| MailDev Web UI | 1080 | HTTP |
| MailDev SMTP | 1025 | SMTP |
| OpenLDAP | 389 / 636 | LDAP / LDAPS |
| phpLDAPadmin | 6443 | HTTPS |
| oauth2-proxy | 4180 | HTTP |

## Practical Work Exercises (FIXME markers)

The code contains intentional gaps that trainees fill in:

### 1. QuestionAuthenticator (`keycloak/provider`)
**File**: `QuestionAuthenticator.java`
**Goal**: Validate a user's secret answer against stored attributes

### 2. UpdateQuestionAction (`keycloak/provider`)
**File**: `UpdateQuestionAction.java`
**Goal**: Read and store the question/answer pair during first login

### 3. AgeMapper (`keycloak/provider`)
**File**: `AgeMapper.java`
**Goal**: Read the `age` user attribute and inject an `isAdult` claim

### 4. Keycloak JS Integration (`vue-app`)
**File**: `main.js`
**Goal**: Uncomment the login flow and HTTP token interceptor

### 5. SPI Provider Registration
**Files**: `META-INF/services/*`
**Goal**: Uncomment registration lines to activate custom providers

## Tests

```bash
# Java unit tests (48 total)
export JAVA_HOME=$(sdk home java 25.0.3-tem 2>/dev/null || echo $JAVA_HOME)
export PATH="$JAVA_HOME/bin:$PATH"

mvn clean test -f keycloak/provider/pom.xml    # 22 tests
mvn clean test -f api/pom.xml                  #  8 tests
mvn clean test -f secret-webapp/pom.xml        # 10 tests

# Vue unit tests (8 tests)
npm --prefix vue-app test

# E2E smoke test (requires Docker)
./scripts/e2e-test.sh
```

## Building the Keycloak SPI Provider

The custom theme and SPI extensions are commented out by default. To activate them:

```bash
# 1. Build the provider JAR
cd keycloak/provider
mvn clean package

# 2. Uncomment the COPY lines in keycloak/Dockerfile:
#    COPY theme/ /opt/keycloak/themes/
#    COPY provider/target/*.jar /opt/keycloak/providers/

# 3. Rebuild and restart
cd ../..
docker compose build keycloak
docker compose up -d keycloak
```

## Project Structure

```
formation-keycloak/
├── api/                          # Spring Boot 4.0 — OAuth2 Resource Server
│   ├── Dockerfile                # Multi-stage: Maven → JRE
│   ├── pom.xml
│   └── src/
│       ├── main/java/...         # REST endpoints protected by JWT
│       └── test/java/...         # Spring MVC + Security tests
├── keycloak/
│   ├── Dockerfile                # Multi-stage Keycloak with custom providers
│   ├── docker-compose.yml        # Infra-only stack (for PW3/6 steps)
│   ├── conf/keycloak.conf        # Keycloak configuration
│   ├── provider/                 # SPI extensions (Java 25, JUnit 5)
│   │   ├── pom.xml
│   │   └── src/
│   │       ├── main/java/...     # Authenticator, RequiredAction, Mapper
│   │       └── test/java/...     # Unit tests (Mockito 5.23, AssertJ)
│   ├── theme/custom/             # Custom login theme (FreeMarker)
│   └── enable_http.sh            # CLI helper for dev mode
├── secret-webapp/                # Spring Boot 4.0 — Multi-auth OAuth2 Client
│   ├── Dockerfile                # Multi-stage: Maven → JRE
│   ├── pom.xml
│   └── src/
│       ├── main/java/...         # none / basic / form / keycloak auth modes
│       └── test/java/...         # Config tests per auth mode
├── vue-app/                      # Vue 3.5 + Vite 8 + keycloak-js 26
│   ├── Dockerfile                # Multi-stage: Node → nginx
│   ├── nginx.conf                # nginx SPA config (port 8070)
│   ├── vite.config.js
│   └── src/
│       ├── main.js               # Keycloak login + HTTP interceptor
│       └── keycloak.js           # Keycloak adapter wrapper
├── docker-compose.yml            # Full stack — one-command startup
├── scripts/
│   ├── audit.sh                  # Dependency update checker
│   └── e2e-test.sh               # End-to-end smoke test
└── strigo/
    └── script.sh                 # Strigo Lab VM provisioning
```
