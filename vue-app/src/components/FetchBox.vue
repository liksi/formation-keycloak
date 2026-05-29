<template>
  <div class="fetchbox" :class="kind" :data-testid="`fetchbox-${kind}`">
    <div class="box-header">
      <div class="box-title-row">
        <span class="box-type-badge" :class="kind">{{ kind }}</span>
        <h3 class="box-title">/messages/{{ kind }}</h3>
      </div>
      <div class="role-status" :class="hasRole ? 'allowed' : 'denied'">
        <span class="role-dot"></span>
        {{ hasRole ? 'ROLE granted' : 'ROLE missing' }}
      </div>
    </div>

    <div class="box-body">
      <p class="box-desc">
        <span v-if="kind === 'admin'">Requires <code>ROLE_ADMIN</code></span>
        <span v-else>Requires <code>ROLE_USER</code></span>
      </p>

      <button
        class="fetch-btn"
        :class="{ loading: isLoading }"
        @click="doFetch"
        :data-testid="`fetch-btn-${kind}`"
        :disabled="isLoading"
      >
        <span class="btn-label">{{ isLoading ? 'Fetching…' : 'Send request' }}</span>
      </button>

      <div class="result-block" v-if="msg" :data-testid="`fetch-result-${kind}`">
        <span class="result-label">Response</span>
        <p class="result-text" :class="{ error: isError }">{{ msg }}</p>
      </div>
      <p v-else class="result-placeholder" :data-testid="`fetch-result-${kind}`"></p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { getRoles } from '@/keycloak'

const props = defineProps(['kind'])

const msg = ref('')
const isLoading = ref(false)
const isError = ref(false)

const hasRole = computed(() =>
  getRoles().includes('ROLE_' + props.kind.toUpperCase())
)

function doFetch () {
  isLoading.value = true
  isError.value = false
  msg.value = ''

  fetch('http://localhost:8091/messages/' + props.kind)
    .then(res => {
      if (!res.ok) return Promise.reject(res)
      return res.json()
    })
    .then(data => {
      msg.value = data.message
    })
    .catch(err => {
      isError.value = true
      if (err instanceof Response) {
        msg.value = `${err.status} — ${err.statusText || 'Unauthorized'}`
      } else {
        msg.value = 'Network error — is the API running?'
      }
    })
    .finally(() => {
      isLoading.value = false
    })
}
</script>

<style scoped>
.fetchbox {
  background: var(--surface);
  border: 1px solid var(--border);
  border-top: 3px solid var(--border-strong);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
  animation: slide-up 0.35s ease;
}

.fetchbox:hover {
  box-shadow: var(--shadow);
  transform: translateY(-2px);
}

.fetchbox.admin { border-top-color: var(--admin); }
.fetchbox.user  { border-top-color: var(--accent); }

/* ── Header ───────────────────────────────────────────── */

.box-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  background: #fafbfc;
}

.box-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.box-type-badge {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 500;
  padding: 3px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.box-type-badge.admin {
  background: var(--admin-bg);
  color: var(--admin);
  border: 1px solid var(--admin-border);
}

.box-type-badge.user {
  background: var(--user-bg);
  color: var(--accent-dark);
  border: 1px solid var(--user-border);
}

.box-title {
  font-family: var(--font-mono);
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-2);
  margin: 0;
}

.role-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 4px 10px;
  border-radius: 999px;
}

.role-status.allowed {
  color: var(--accent-dark);
  background: var(--user-bg);
  border: 1px solid var(--user-border);
}

.role-status.denied {
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
}

.role-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.role-status.allowed .role-dot { background: var(--accent); }
.role-status.denied  .role-dot { background: #f59e0b; }

/* ── Body ─────────────────────────────────────────────── */

.box-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  flex: 1;
}

.box-desc {
  font-size: 0.78rem;
  color: var(--text-3);
  margin: 0;
}

.box-desc code {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--border);
  color: var(--text-2);
}

.fetch-btn {
  align-self: flex-start;
  font-family: var(--font-body);
  font-size: 0.82rem;
  font-weight: 600;
  padding: 9px 18px;
  border-radius: var(--r-sm);
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.15s ease, opacity 0.15s ease, transform 0.1s ease;
  background: var(--text-1);
  color: #ffffff;
  letter-spacing: 0.01em;
}

.fetchbox.admin .fetch-btn { background: var(--admin); }
.fetchbox.user  .fetch-btn { background: var(--accent-dark); }

.fetch-btn:hover:not(:disabled) {
  opacity: 0.88;
  transform: translateY(-1px);
}

.fetch-btn:active:not(:disabled) {
  transform: translateY(0);
}

.fetch-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.fetch-btn.loading .btn-label::after {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin-left: 8px;
  vertical-align: middle;
}

/* ── Result ───────────────────────────────────────────── */

.result-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.result-label {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-3);
}

.result-text {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text-1);
  margin: 0;
  padding: 10px 14px;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  word-break: break-all;
  animation: fade-in 0.2s ease;
}

.result-text.error {
  color: var(--admin);
  background: var(--admin-bg);
  border-color: var(--admin-border);
}

.result-placeholder {
  margin: 0;
  min-height: 38px;
}

/* ── Animations ───────────────────────────────────────── */

@keyframes slide-up {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
