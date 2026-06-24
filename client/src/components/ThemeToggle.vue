<template>
  <button
    class="theme-toggle-button"
    @click="toggleTheme"
    :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
    :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
  >
    <!-- Sun icon: shown in dark mode, clicking switches to light -->
    <svg
      v-if="isDark"
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linecap="round"
    >
      <circle cx="10" cy="10" r="3.5"/>
      <line x1="10" y1="2" x2="10" y2="4"/>
      <line x1="10" y1="16" x2="10" y2="18"/>
      <line x1="2" y1="10" x2="4" y2="10"/>
      <line x1="16" y1="10" x2="18" y2="10"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="14.36" y1="14.36" x2="15.78" y2="15.78"/>
      <line x1="4.22" y1="15.78" x2="5.64" y2="14.36"/>
      <line x1="14.36" y1="5.64" x2="15.78" y2="4.22"/>
    </svg>

    <!-- Moon icon: shown in light mode, clicking switches to dark -->
    <svg
      v-else
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M17 11.5A7 7 0 1 1 8.5 3a5.5 5.5 0 0 0 8.5 8.5z"/>
    </svg>
  </button>
</template>

<script setup>
import { useTheme } from '../composables/useTheme'

const { isDark, toggleTheme } = useTheme()
</script>

<style scoped>
.theme-toggle-button {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 0.875rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.theme-toggle-button:hover {
  background: var(--bg-subtle);
  border-color: var(--border-strong);
}
</style>
