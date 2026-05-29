<template>
  <header class="header" data-testid="app-header">
    <div class="header-inner">
      <div class="brand">
        <img src="../assets/keycloak_logo.png" alt="Keycloak logo" class="logo" />
        <div class="brand-text">
          <span class="brand-name">Keycloak</span>
          <span class="brand-sub">Demo App</span>
        </div>
      </div>
      <nav class="nav">
        <a href="/" class="nav-link" data-testid="nav-home">Home</a>
        <button class="nav-link" @click="account" data-testid="nav-account">My account</button>
        <button class="nav-link nav-logout" @click="logout" data-testid="nav-logout">Log out</button>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { logout as keycloakLogout, gotoAccount } from '../keycloak'
function logout () { keycloakLogout() }
function account () { gotoAccount() }
</script>

<style scoped>
.header {
  background: var(--header-bg);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-inner {
  padding: 0 5%;
  height: 62px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo {
  height: 26px;
  width: auto;
  filter: brightness(0) invert(1);
  opacity: 0.85;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1;
  gap: 3px;
}

.brand-name {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.02em;
}

.brand-sub {
  font-size: 0.6rem;
  color: var(--accent);
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.nav {
  display: flex;
  align-items: center;
  gap: 2px;
}

.nav-link {
  font-family: var(--font-body);
  font-size: 0.8rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.5);
  text-decoration: none;
  padding: 6px 14px;
  border-radius: var(--r-sm);
  border: none;
  background: transparent;
  cursor: pointer;
  transition: color 0.15s ease, background 0.15s ease;
  letter-spacing: 0.01em;
}

.nav-link:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.07);
}

.nav-logout {
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.45);
}

.nav-logout:hover {
  border-color: rgba(220, 38, 38, 0.4);
  color: #fca5a5;
  background: rgba(220, 38, 38, 0.08);
}
</style>
