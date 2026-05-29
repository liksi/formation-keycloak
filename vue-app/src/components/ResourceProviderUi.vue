<template>
  <main class="page" data-testid="resource-provider-ui">
    <div class="page-inner">

      <div class="greeting-row">
        <div class="greeting-block">
          <p class="greeting-label">Welcome back</p>
          <h1 class="greeting" data-testid="greeting">{{ name }}</h1>
        </div>
        <div class="session-pill" v-if="tokenParsed">
          <span class="session-dot"></span>
          <span>Authenticated</span>
        </div>
      </div>

      <section class="token-card" data-testid="token-info" v-if="tokenParsed">
        <div class="card-header">
          <div class="card-title-group">
            <span class="card-eyebrow">Access Token</span>
            <h2 class="card-title">JWT Claims</h2>
          </div>
          <div
            class="expiry-badge"
            :class="{ warning: expirySeconds < 60 && expirySeconds > 0, expired: expirySeconds <= 0 }"
            data-testid="token-expiry"
          >
            <span class="expiry-dot"></span>
            <span class="expiry-label">expires in</span>
            <span class="expiry-value">{{ expiryDisplay }}</span>
          </div>
        </div>

        <div class="token-rows">
          <div class="token-row">
            <span class="token-key">preferred_username</span>
            <span class="token-val" data-testid="token-username">{{ tokenParsed.preferred_username ?? '—' }}</span>
          </div>
          <div class="token-row">
            <span class="token-key">email</span>
            <span class="token-val" data-testid="token-email">{{ tokenParsed.email ?? '—' }}</span>
          </div>
          <div class="token-row">
            <span class="token-key">realm_access.roles</span>
            <span class="token-val" data-testid="token-roles">
              <span v-if="roles.length === 0" class="no-role">[ ]</span>
              <span
                v-for="role in roles"
                :key="role"
                class="role-badge"
                :class="{ admin: role.includes('ADMIN'), user: role.includes('USER') }"
              >{{ role }}</span>
            </span>
          </div>
        </div>
      </section>

      <div class="api-section">
        <div class="section-header">
          <h2 class="section-title">API Resources</h2>
          <p class="section-desc">Role-protected endpoints on the resource server</p>
        </div>
        <div class="fetchboxes">
          <FetchBox kind="admin" />
          <FetchBox kind="user" />
        </div>
      </div>

    </div>
  </main>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import FetchBox from './FetchBox.vue'
import { getUsername, getRoles, getTokenParsed } from '../keycloak'

const name = getUsername()
const roles = getRoles()

const now = ref(Math.floor(Date.now() / 1000))
const tokenParsed = ref(getTokenParsed())

let timer
onMounted(() => {
  timer = setInterval(() => {
    now.value = Math.floor(Date.now() / 1000)
    tokenParsed.value = getTokenParsed()
  }, 1000)
})
onUnmounted(() => clearInterval(timer))

const expirySeconds = computed(() => {
  if (!tokenParsed.value?.exp) return 0
  return tokenParsed.value.exp - now.value
})

const expiryDisplay = computed(() => {
  const s = expirySeconds.value
  if (s <= 0) return 'Expired'
  const m = Math.floor(s / 60)
  const sec = s % 60
  return m > 0 ? `${m}m ${sec}s` : `${sec}s`
})
</script>

<style scoped>
.page {
  flex: 1;
  padding: 48px 5% 80px;
}

.page-inner {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* ── Greeting ─────────────────────────────────────────── */

.greeting-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}

.greeting-label {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-3);
  margin: 0 0 6px;
}

.greeting {
  font-family: var(--font-display);
  font-size: 2.25rem;
  font-weight: 800;
  color: var(--text-1);
  margin: 0;
  letter-spacing: -0.03em;
  line-height: 1;
}

.session-pill {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 14px;
  background: var(--user-bg);
  border: 1px solid var(--user-border);
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--accent-dark);
  letter-spacing: 0.03em;
  animation: fade-in 0.4s ease;
}

.session-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.6; transform: scale(0.85); }
}

/* ── Token card ───────────────────────────────────────── */

.token-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow);
  overflow: hidden;
  animation: slide-up 0.35s ease;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 20px 28px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(to right, #fafbfc, var(--surface));
}

.card-eyebrow {
  display: block;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-3);
  margin-bottom: 3px;
}

.card-title {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-1);
  margin: 0;
  letter-spacing: -0.02em;
}

.expiry-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  border-radius: 999px;
  background: var(--user-bg);
  border: 1px solid var(--user-border);
  transition: background 0.3s, border-color 0.3s;
}

.expiry-badge.warning {
  background: #fffbeb;
  border-color: #fde68a;
}

.expiry-badge.expired {
  background: #fef2f2;
  border-color: #fecaca;
}

.expiry-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
  transition: background 0.3s;
}

.expiry-badge.warning .expiry-dot { background: var(--warning); }
.expiry-badge.expired  .expiry-dot { background: var(--danger); animation: none; }

.expiry-label {
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--text-3);
  letter-spacing: 0.04em;
}

.expiry-value {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--accent-dark);
  min-width: 52px;
}

.expiry-badge.warning .expiry-value { color: var(--warning); }
.expiry-badge.expired  .expiry-value { color: var(--danger); }

.token-rows {
  padding: 8px 0;
}

.token-row {
  display: flex;
  align-items: baseline;
  gap: 24px;
  padding: 13px 28px;
  border-bottom: 1px solid var(--border);
  transition: background 0.1s;
}

.token-row:last-child {
  border-bottom: none;
}

.token-row:hover {
  background: #fafbfd;
}

.token-key {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--text-3);
  flex-shrink: 0;
  width: 210px;
}

.token-val {
  font-family: var(--font-mono);
  font-size: 0.82rem;
  font-weight: 400;
  color: var(--text-1);
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.role-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 500;
  background: var(--user-bg);
  color: var(--accent-dark);
  border: 1px solid var(--user-border);
}

.role-badge.admin {
  background: var(--admin-bg);
  color: var(--admin);
  border-color: var(--admin-border);
}

.no-role {
  color: var(--text-3);
}

/* ── API section ──────────────────────────────────────── */

.api-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-header {
  display: flex;
  align-items: baseline;
  gap: 14px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-1);
  margin: 0;
  letter-spacing: -0.02em;
}

.section-desc {
  font-size: 0.8rem;
  color: var(--text-3);
  margin: 0;
}

.fetchboxes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 20px;
}

/* ── Animations ───────────────────────────────────────── */

@keyframes fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@keyframes slide-up {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>
