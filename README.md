# Formation Keycloak

Support de formation Keycloak par [Liksi](https://www.liksi.fr) — atelier hands-on pour apprendre Keycloak, OAuth2/OIDC, et la sécurisation d'applications.

## Architecture

```
                          ┌─────────────────────┐
                          │    Keycloak 26.x     │
                          │  ┌───────────────┐   │
                          │  │ SPI Provider   │   │
                          │  │ • Authenticator│   │
                          │  │ • RequiredAction│  │
                          │  │ • Mapper       │   │
                          │  └───────────────┘   │
                          └──────────┬───────────┘
                                     │ OAuth2/OIDC
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
    ┌─────▼──────┐           ┌───────▼───────┐          ┌───────▼───────┐
    │  vue-app   │           │ secret-webapp │          │      api      │
    │  Vue 3     │           │ Spring Boot   │          │  Spring Boot  │
    │  (SPA)     │           │ (OAuth client │          │  (OAuth RS)   │
    │  :8070     │           │   multi-auth) │          │   :8091       │
    └────────────┘           │   :8090       │          └───────────────┘
                             └───────────────┘

Services auxiliaires :
┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐
│PostgreSQL│ │ OpenLDAP │ │ phpLDAPadmin │ │ MailDev  │ │oauth2-   │
│   :5432  │ │ :389:636 │ │    :6443     │ │  :1025   │ │proxy     │
└──────────┘ └──────────┘ └──────────────┘ │  :1080   │ │  :4180   │
                                           └──────────┘ └──────────┘
```

## Prérequis

- **Docker** et Docker Compose (v2+)
- **Java 21** (Temurin recommandé)
- **Maven 3.9+**
- **Node.js 22+** et npm

## Démarrage rapide

### 1. Infrastructure Docker

```bash
cd keycloak
docker compose up -d
```

Cela démarre Keycloak, PostgreSQL, OpenLDAP, phpLDAPadmin, MailDev et oauth2-proxy.

| Service | URL |
|---------|-----|
| Keycloak | http://localhost:8080 |
| Keycloak admin | admin / admin |
| MailDev | http://localhost:1080 |
| LDAP admin | https://localhost:6443 |
| oauth2-proxy | http://localhost:4180 |

### 2. Builder le provider SPI

```bash
cd keycloak/provider
mvn clean package
cp target/registration-spi-1.0.0-SNAPSHOT.jar ../providers/
```

Puis décommenter les lignes `COPY` dans `keycloak/Dockerfile` et rebuild :

```bash
cd keycloak
docker compose build keycloak
docker compose up -d keycloak
```

### 3. Lancer les applications

```bash
# API Resource Server
cd api
mvn spring-boot:run

# Secret Webapp (mode d'auth configurable dans application.yml)
cd secret-webapp
mvn spring-boot:run

# Vue App
cd vue-app
npm install
npm run dev
```

## Ports exposés

| Application | Port |
|-------------|------|
| Keycloak (HTTP) | 8080 |
| Keycloak (HTTPS) | 8443 |
| Keycloak management | 9990 |
| API Resource Server | 8091 |
| Secret Webapp | 8090 |
| Vue App (dev) | 8070 |
| MailDev web UI | 1080 |
| MailDev SMTP | 1025 |
| OpenLDAP | 389 / 636 |
| phpLDAPadmin | 6443 |
| oauth2-proxy | 4180 |

## Exercices de formation (FIXME)

Le code contient des exercices volontairement incomplets :

### 1. QuestionAuthenticator (`keycloak/provider`)
- **Fichier** : `QuestionAuthenticator.java`
- **Objectif** : Valider la réponse secrète d'un utilisateur contre un attribut stocké (`question`/`answer`)

### 2. UpdateQuestionAction (`keycloak/provider`)
- **Fichier** : `UpdateQuestionAction.java`
- **Objectif** : Lire et stocker la question/réponse dans les attributs utilisateur

### 3. AgeMapper (`keycloak/provider`)
- **Fichier** : `AgeMapper.java`
- **Objectif** : Lire l'attribut `age` et ajouter un claim `isAdult` au token

### 4. Intégration Keycloak JS (`vue-app`)
- **Fichier** : `main.js`
- **Objectif** : Décommenter le flux de login et l'intercepteur HTTP

### 5. Enregistrement des providers SPI
- **Fichiers** : `META-INF/services/*`
- **Objectif** : Décommenter les lignes pour activer les providers

## Tests

```bash
# Tests unitaires Java
mvn clean test -f api/pom.xml
mvn clean test -f secret-webapp/pom.xml
mvn clean test -f keycloak/provider/pom.xml

# Tests Vue
npm --prefix vue-app test

# Smoke test E2E (nécessite Docker)
./scripts/e2e-test.sh
```

## Structure du projet

```
formation-keycloak/
├── api/                        # Spring Boot - Resource Server OAuth2
│   └── src/
│       ├── main/java/...       # Endpoints REST protégés par JWT
│       └── test/java/...       # Tests Spring MVC + sécurité
├── keycloak/
│   ├── Dockerfile              # Image Keycloak custom
│   ├── docker-compose.yml      # Stack Docker complète
│   ├── conf/keycloak.conf      # Configuration Keycloak
│   ├── provider/               # Extensions SPI Keycloak
│   │   └── src/
│   │       ├── main/java/...   # Authenticator, RequiredAction, Mapper
│   │       └── test/java/...   # Tests unitaires des providers
│   ├── theme/custom/           # Thème de login personnalisé
│   └── enable_http.sh          # Script utilitaire (dev)
├── secret-webapp/              # Spring Boot - Client OAuth2 multi-mode
│   └── src/
│       ├── main/java/...       # Configs: none/basic/form/keycloak
│       └── test/java/...       # Tests par mode d'authentification
├── vue-app/                    # Frontend Vue 3 + Vite
│   ├── src/                    # Composants + intégration keycloak-js
│   └── tests/                  # Tests unitaires Vitest
├── scripts/                    # Scripts utilitaires
│   └── e2e-test.sh             # Smoke test end-to-end
└── strigo/                     # Provisioning VM pour la formation
    └── script.sh
```
