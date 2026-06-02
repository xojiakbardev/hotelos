/**
 * Optimistic UI helper.
 *
 * Usage:
 *   const run = useOptimistic({
 *     apply: () => entry.status = 'in_progress',
 *     revert: () => entry.status = before,
 *     call:   () => housekeepingApi.start(entry.id),
 *     ok:     (updated) => store.upsert(updated),
 *     successMsg: (u) => `Started cleaning room ${u.room_number}`,
 *     errorMsg:   (e) => `Failed: ${parseError(e)}`,
 *   })
 *   await run()
 *
 * `apply` runs synchronously before `call` — the UI sees the new state
 * instantly. If the API call fails, `revert` rolls back and the error
 * toast fires. On success, `ok` lets you replace the optimistic state
 * with the authoritative server result.
 */

import { useToastStore } from '@/stores/toast'

export interface OptimisticOptions<TResult> {
  apply: () => void
  revert: () => void
  call: () => Promise<TResult>
  ok?: (result: TResult) => void
  successMsg?: (result: TResult) => string | null
  errorMsg?: (err: unknown) => string
}

export function useOptimistic<TResult>(opts: OptimisticOptions<TResult>) {
  const toast = useToastStore()

  return async (): Promise<TResult | null> => {
    opts.apply()
    try {
      const result = await opts.call()
      opts.ok?.(result)
      const ok = opts.successMsg?.(result)
      if (ok) toast.success(ok)
      return result
    } catch (err) {
      opts.revert()
      toast.error(opts.errorMsg ? opts.errorMsg(err) : 'request failed')
      return null
    }
  }
}

/** Pull a human-readable error message out of an Axios error envelope. */
export function parseApiError(err: unknown): string {
  const e = err as {
    response?: { data?: { message?: string; error?: string; details?: unknown[] } }
    message?: string
  }
  const data = e.response?.data
  if (data?.message) return data.message
  if (data?.error) return data.error
  return e.message ?? 'request failed'
}
