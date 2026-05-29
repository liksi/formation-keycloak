<template>
  <div id="app">
    <HeaderComponent />
    <router-view />
  </div>
</template>

<script setup>
import HeaderComponent from './components/HeaderComponent.vue'
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg:            #f1f5f9;
  --surface:       #ffffff;
  --border:        #e2e8f0;
  --border-strong: #cbd5e1;
  --text-1:        #0f172a;
  --text-2:        #475569;
  --text-3:        #94a3b8;
  --accent:        #42b983;
  --accent-dark:   #2d8a63;
  --accent-glow:   rgba(66, 185, 131, 0.12);
  --header-bg:     #0f172a;
  --admin:         #dc2626;
  --admin-bg:      #fef2f2;
  --admin-border:  #fecaca;
  --user:          #42b983;
  --user-bg:       #f0fdf4;
  --user-border:   #bbf7d0;
  --warning:       #d97706;
  --danger:        #dc2626;
  --r-sm:          6px;
  --r:             10px;
  --r-lg:          16px;
  --shadow-sm:     0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04);
  --shadow:        0 4px 12px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.04);
  --shadow-lg:     0 12px 24px rgba(0,0,0,0.09), 0 4px 8px rgba(0,0,0,0.04);
  --font-display:  'Syne', sans-serif;
  --font-body:     'DM Sans', sans-serif;
  --font-mono:     'JetBrains Mono', monospace;
}

*, *::before, *::after { box-sizing: border-box; }

body {
  margin: 0;
  background-color: var(--bg);
  background-image: radial-gradient(circle, #c8d5e8 1px, transparent 1px);
  background-size: 22px 22px;
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--text-1);
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
