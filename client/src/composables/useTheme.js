import { ref, computed } from 'vue'

// Module-level ref so theme state is shared across all composable calls
const currentTheme = ref(localStorage.getItem('app-theme') || 'light')

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
    currentTheme: computed(() => currentTheme.value),
    isDark,
    toggleTheme
  }
}
