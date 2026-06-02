import { defineStore } from 'pinia'

export type ToastKind = 'info' | 'success' | 'warning' | 'error'

export interface ToastItem {
  id: number
  kind: ToastKind
  message: string
}

let nextId = 1

export const useToastStore = defineStore('toast', {
  state: () => ({ items: [] as ToastItem[] }),
  actions: {
    push(kind: ToastKind, message: string, ttlMs = 4000) {
      const id = nextId++
      this.items.push({ id, kind, message })
      window.setTimeout(() => this.dismiss(id), ttlMs)
      return id
    },
    info(msg: string) { return this.push('info', msg) },
    success(msg: string) { return this.push('success', msg) },
    warning(msg: string) { return this.push('warning', msg) },
    error(msg: string) { return this.push('error', msg) },
    dismiss(id: number) {
      this.items = this.items.filter((t) => t.id !== id)
    }
  }
})
