import { ref, computed, readonly } from 'vue'

// Determine the initial theme: prefer an explicit user choice stored in
// localStorage; fall back to the OS-level prefers-color-scheme preference
// so first-time visitors see the correct theme without any flash.
const getInitialTheme = () => {
  const saved = localStorage.getItem('app-theme')
  if (saved) return saved
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

// Module-level ref so theme state is shared across all composable calls
const currentTheme = ref(getInitialTheme())

// Apply the given theme to the document root so CSS variables take effect.
// Called once at module load to restore the saved theme before first render,
// which avoids a flash of the wrong theme.
const applyTheme = (theme) => {
  document.documentElement.setAttribute('data-theme', theme)
}

// Apply immediately on module load
applyTheme(currentTheme.value)

export function useTheme() {
  const isDark = computed(() => currentTheme.value === 'dark')

  const toggleTheme = () => {
    const next = currentTheme.value === 'light' ? 'dark' : 'light'
    currentTheme.value = next
    localStorage.setItem('app-theme', next)
    applyTheme(next)
  }

  return {
    // readonly() exposes the shared ref without an extra computed wrapper;
    // consumers can read .value but cannot mutate it directly.
    currentTheme: readonly(currentTheme),
    isDark,
    toggleTheme
  }
}
