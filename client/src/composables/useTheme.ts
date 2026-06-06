import { ref, computed, watch, onMounted } from 'vue'

export type ThemePreference = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

const STORAGE_KEY = 'hotelos.theme'

const theme = ref<ThemePreference>('system')

function getStoredTheme(): ThemePreference {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  } catch {
    // localStorage blocked — graceful fallback
  }
  return 'system'
}

function getSystemPreference(): ResolvedTheme {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(resolved: ResolvedTheme) {
  const root = document.documentElement
  if (resolved === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

export function useTheme() {
  const resolvedTheme = computed<ResolvedTheme>(() => {
    if (theme.value === 'system') return getSystemPreference()
    return theme.value
  })

  function setTheme(t: ThemePreference) {
    theme.value = t
    try {
      localStorage.setItem(STORAGE_KEY, t)
    } catch {
      // localStorage blocked — ignore
    }
    applyTheme(resolvedTheme.value)
  }

  function toggleTheme() {
    const cycle: ThemePreference[] = ['light', 'dark', 'system']
    const idx = cycle.indexOf(theme.value)
    setTheme(cycle[(idx + 1) % cycle.length])
  }

  // Initialize on first use
  onMounted(() => {
    theme.value = getStoredTheme()
    applyTheme(resolvedTheme.value)

    // Listen for system preference changes
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => {
      if (theme.value === 'system') {
        applyTheme(getSystemPreference())
      }
    }
    mq.addEventListener('change', handler)
  })

  // Watch for theme changes
  watch(resolvedTheme, (val) => applyTheme(val))

  return {
    theme,
    resolvedTheme,
    toggleTheme,
    setTheme,
  }
}
