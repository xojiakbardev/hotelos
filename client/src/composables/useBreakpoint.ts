import { ref, computed, onMounted, onUnmounted } from 'vue'

const width = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)

let listenerCount = 0
let resizeHandler: (() => void) | null = null

function onResize() {
  width.value = window.innerWidth
}

export function useBreakpoint() {
  const isMobile = computed(() => width.value < 640)
  const isTablet = computed(() => width.value >= 640 && width.value <= 1024)
  const isDesktop = computed(() => width.value > 1024)

  onMounted(() => {
    width.value = window.innerWidth
    if (listenerCount === 0) {
      resizeHandler = onResize
      window.addEventListener('resize', resizeHandler, { passive: true })
    }
    listenerCount++
  })

  onUnmounted(() => {
    listenerCount--
    if (listenerCount === 0 && resizeHandler) {
      window.removeEventListener('resize', resizeHandler)
      resizeHandler = null
    }
  })

  return {
    isMobile,
    isTablet,
    isDesktop,
    width,
  }
}
